"""Sinh Oracle SQL; không kết nối hoặc thực thi Oracle."""
import re


def ident(value):
    """Nhận identifier Oracle hoặc tên bảng có schema/database link.

    Giữ tương thích với các module/bản app cũ còn gọi ``ident(table_name)``.
    Mẫu được chấp nhận: TABLE, SCHEMA.TABLE, TABLE@DBLINK,
    SCHEMA.TABLE@DBLINK.
    """
    value = str(value or "").upper()
    simple = r"[A-Z][A-Z0-9_$#]*"
    if re.fullmatch(simple, value):
        return value
    if re.fullmatch(rf"{simple}(?:\.{simple})?(?:@{simple})?", value):
        return value
    raise ValueError(f"Tên Oracle không hợp lệ: {value}")


def oracle_table_ref(value):
    """Cho phép tên bảng Oracle có schema và database link.

    Ví dụ hợp lệ: SAJET.SMT_BDCODE_MEDGRECORD@YASHOKZFATP_VNMESZ.
    Từng phần vẫn phải là identifier Oracle, nên không cho chèn SQL tùy ý.
    """
    value = str(value or "").upper()
    match = re.fullmatch(r"([A-Z][A-Z0-9_$#]*)(?:\.([A-Z][A-Z0-9_$#]*))?(?:@([A-Z][A-Z0-9_$#]*))?", value)
    if not match:
        raise ValueError(f"Tên bảng Oracle không hợp lệ: {value}")
    owner, table, dblink = match.groups()
    result = f"{owner}.{table}" if table else owner
    return f"{result}@{dblink}" if dblink else result


def table_alias_prefix(table_name):
    """Alias SELECT từ tên bảng đầy đủ: SCHEMA.TABLE@LINK → TABLE."""
    return ident(str(table_name).split("@")[0].split(".")[-1])


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def value_sql(value, data_type):
    if str(data_type).upper().startswith("DATE"):
        return f"TO_DATE({quote(value)}, 'YYYY-MM-DD')"
    if str(data_type).upper().startswith(("NUMBER", "INTEGER", "DECIMAL", "FLOAT")):
        return str(value)
    return quote(value)


def condition_sql(c):
    col, op, data_type = c["ref"], c["op"], c.get("data_type", "")
    if op in ("IS NULL", "IS NOT NULL"):
        return f"{col} {op}"
    if op == "BETWEEN":
        return f"{col} BETWEEN {value_sql(c.get('value', ''), data_type)} AND {value_sql(c.get('value2', ''), data_type)}"
    if op == "RANGE_EXCLUSIVE_END":
        return f"{col} >= {c.get('value')} AND {col} < {c.get('value2')}"
    if op == "IN":
        vals = [v.strip() for v in str(c.get("value", "")).split(",") if v.strip()]
        return f"{col} IN ({', '.join(value_sql(v, data_type) for v in vals)})"
    if op == "LIKE":
        return f"{col} LIKE {quote('%' + str(c.get('value', '')) + '%')}"
    return f"{col} {op} {value_sql(c.get('value', ''), data_type)}"


def build_sql(state):
    main = state.get("main")
    if not main:
        return "-- Chọn bảng chính để tạo SQL"
    table, alias = oracle_table_ref(main["table_name"]), "t1"
    selected = state.get("selected", [])
    # SELECT * chỉ áp dụng cho bảng chính; cột JOIN luôn được đặt alias rõ ràng.
    fields = [f"{alias}.*"] if state.get("select_all_main") else [f"{alias}.{ident(c['column_name'])}" for c in selected]
    links = state.get("links", [])
    for index, link in enumerate(links, 2):
        for col in link.get("selected", []):
            fields.append(f"t{index}.{ident(col['column_name'])} AS {table_alias_prefix(link['table']['table_name'])}_{ident(col['column_name'])}")
    if not fields:
        fields = [f"{alias}.*"]
    lines = ["SELECT " + ",\n       ".join(fields), f"FROM {table} {alias}"]
    for index, link in enumerate(links, 2):
        join_type = link.get("join_type", "LEFT JOIN")
        if join_type not in {"LEFT JOIN", "INNER JOIN", "RIGHT JOIN", "FULL OUTER JOIN", "CROSS JOIN"}:
            raise ValueError(f"Loại JOIN không hợp lệ: {join_type}")
        join_table = f"{join_type} {oracle_table_ref(link['table']['table_name'])} t{index}"
        if join_type == "CROSS JOIN":
            lines.append(join_table)
        else:
            # left_alias do UI sinh ra: t1 hoặc một bảng JOIN trước đó (t2, t3...).
            left_alias = link.get("left_alias", alias)
            if not re.fullmatch(r"t[1-9][0-9]*", left_alias):
                raise ValueError("Alias bảng nối không hợp lệ")
            lines.append(f"{join_table} ON {left_alias}.{ident(link['left']['column_name'])} = t{index}.{ident(link['right']['column_name'])}")
    conditions = [condition_sql(c) for c in state.get("conditions", [])]
    if conditions:
        lines.append("WHERE " + "\n  AND ".join(conditions))
    group_by = state.get("group_by", [])
    if group_by:
        lines.append("GROUP BY " + ", ".join(group_by))
    having = [condition_sql(c) for c in state.get("having", [])]
    if having:
        lines.append("HAVING " + "\n   AND ".join(having))
    if state.get("order"):
        lines.append(f"ORDER BY {state['order']['ref']} {state['order']['direction']}")
    if state.get("limit") not in (None, "Tất cả"):
        lines.append(f"FETCH FIRST {int(state['limit'])} ROWS ONLY")
    return "\n".join(lines) + ";"
