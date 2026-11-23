"""Chuẩn bị dữ liệu node/edge cho sơ đồ quan hệ bảng."""

DEFAULT_COLOR = "#95A5A6"


def table_description(table):
    """Ưu tiên mô tả tiếng Việt khi metadata đã có cột này."""
    return table.get("description_vi") or table.get("description") or "Chưa có mô tả"


def normalize_selection(selected):
    """streamlit-agraph có thể trả id string hoặc object tuỳ phiên bản."""
    if isinstance(selected, str):
        return selected
    if isinstance(selected, dict):
        return selected.get("id") or selected.get("node")
    return None


def related_table_names(relations, table_name):
    names = set()
    for relation in relations:
        if relation["source_table"] == table_name:
            names.add(relation["target_table"])
        elif relation["target_table"] == table_name:
            names.add(relation["source_table"])
    return names


def filter_graph(tables, relations, group_name="Tất cả", search="", focus_table=None, direct_only=False):
    """Lọc graph theo nhóm/từ khoá hoặc chỉ các node liên quan trực tiếp."""
    search = search.strip().lower()
    visible = {
        table["table_name"] for table in tables
        if group_name == "Tất cả" or table.get("group_name") == group_name
    }
    if direct_only and focus_table:
        visible = {focus_table, *related_table_names(relations, focus_table)}
    if search:
        matches = {
            table["table_name"] for table in tables
            if search in table["table_name"].lower()
            or search in table_description(table).lower()
        }
        # Search highlight thay vì làm mất context của cả sơ đồ.
        visible &= matches if direct_only else visible
    return [table for table in tables if table["table_name"] in visible], [
        relation for relation in relations
        if relation["source_table"] in visible and relation["target_table"] in visible
    ]


def generate_table_join_sql(table_name, relations):
    """Tạo câu lệnh SQL SELECT kèm JOIN đến tất cả các bảng có quan hệ trực tiếp để tiện tra cứu."""
    table_rels = [
        r for r in relations
        if r.get("source_table") == table_name or r.get("target_table") == table_name
    ]
    if not table_rels:
        return f"SELECT t1.*\nFROM {table_name} t1\nFETCH FIRST 100 ROWS ONLY;"

    lines = ["SELECT t1.*"]
    joins = []
    used_aliases = {"t1"}

    for idx, r in enumerate(table_rels, start=2):
        alias = f"t{idx}"
        if r["source_table"] == table_name:
            other = r["target_table"]
            scol = r.get("source_column") or "ID"
            tcol = r.get("target_column") or "ID"
            lines.append(f"     , {alias}.*")
            joins.append(f"LEFT JOIN {other} {alias} ON t1.{scol} = {alias}.{tcol}")
        else:
            other = r["source_table"]
            scol = r.get("source_column") or "ID"
            tcol = r.get("target_column") or "ID"
            lines.append(f"     , {alias}.*")
            joins.append(f"LEFT JOIN {other} {alias} ON t1.{tcol} = {alias}.{scol}")

    return "\n".join(lines) + f"\nFROM {table_name} t1\n" + "\n".join(joins) + "\nFETCH FIRST 100 ROWS ONLY;"

