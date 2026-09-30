"""Sinh INSERT Oracle; tuyệt đối không thực thi SQL."""
from core.sql_builder import ident
from core.value_formatter import format_value_for_oracle


def _statement(table_name, row):
    items = [item for item in row if not item.get("skip")]
    if not items:
        raise ValueError("Mỗi dòng INSERT cần ít nhất một cột.")
    columns = ", ".join(ident(item["column"]["column_name"]) for item in items)
    values = ", ".join(format_value_for_oracle(item.get("value"), item["column"].get("data_type"), item.get("use_default"), item.get("use_null")) for item in items)
    return columns, values


def build_insert_sql(table_name, rows, oracle_version="19c"):
    """23c dùng multi-row VALUES; bản cũ sinh nhiều INSERT tương thích rộng."""
    if not rows:
        return "-- Thêm ít nhất một dòng để sinh INSERT"
    rendered = [_statement(table_name, row) for row in rows]
    table = ident(table_name)
    is_23_or_newer = str(oracle_version).lower().startswith("23")
    same_columns = len({cols for cols, _ in rendered}) == 1
    if is_23_or_newer and len(rendered) > 1 and same_columns:
        return f"INSERT INTO {table} ({rendered[0][0]})\nVALUES\n  " + ",\n  ".join(f"({values})" for _, values in rendered) + ";"
    return "\n\n".join(f"INSERT INTO {table} ({columns})\nVALUES ({values});" for columns, values in rendered)
