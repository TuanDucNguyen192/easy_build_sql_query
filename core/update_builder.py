"""Sinh UPDATE Oracle; tuyệt đối không thực thi SQL."""
from core.sql_builder import ident, condition_sql
from core.value_formatter import format_value_for_oracle


def build_update_sql(table_name, assignments, conditions):
    if not assignments:
        return "-- Chọn ít nhất một cột cần cập nhật"
    sets = []
    for item in assignments:
        col = ident(item["column"]["column_name"])
        value = format_value_for_oracle(item.get("value"), item["column"].get("data_type"), item.get("use_default"), item.get("use_null"))
        sets.append(f"{col} = {value}")
    lines = [f"UPDATE {ident(table_name)}", "SET " + ",\n    ".join(sets)]
    if conditions:
        lines.append("WHERE " + "\n  AND ".join(condition_sql(item) for item in conditions))
    return "\n".join(lines) + ";"
