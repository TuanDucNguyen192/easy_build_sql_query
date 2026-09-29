"""Sinh Oracle SQL; không kết nối hoặc thực thi Oracle."""
import re


def ident(value):
    """Chỉ nhận identifier Oracle để tránh sinh SQL sai từ metadata."""
    value = str(value or "").upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_$#]*", value):
        raise ValueError(f"Tên Oracle không hợp lệ: {value}")
    return value


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
    table, alias = ident(main["table_name"]), "t1"
    selected = state.get("selected", [])
    fields = [f"{alias}.{ident(c['column_name'])}" for c in selected]
    links = state.get("links", [])
    for index, link in enumerate(links, 2):
        for col in link.get("selected", []):
            fields.append(f"t{index}.{ident(col['column_name'])} AS {ident(link['table']['table_name'])}_{ident(col['column_name'])}")
    if not fields:
        fields = [f"{alias}.*"]
    lines = ["SELECT " + ",\n       ".join(fields), f"FROM {table} {alias}"]
    for index, link in enumerate(links, 2):
        lines.append(f"LEFT JOIN {ident(link['table']['table_name'])} t{index} ON {alias}.{ident(link['left']['column_name'])} = t{index}.{ident(link['right']['column_name'])}")
    conditions = [condition_sql(c) for c in state.get("conditions", [])]
    if conditions:
        lines.append("WHERE " + "\n  AND ".join(conditions))
    if state.get("order"):
        lines.append(f"ORDER BY {state['order']['ref']} {state['order']['direction']}")
    if state.get("limit") not in (None, "Tất cả"):
        lines.append(f"FETCH FIRST {int(state['limit'])} ROWS ONLY")
    return "\n".join(lines) + ";"
