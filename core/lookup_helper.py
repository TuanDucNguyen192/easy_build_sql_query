"""Tìm lookup phù hợp với một cột Oracle."""

def lookup_for_column(column_name, lookups):
    # Tên lookup có thể là USER_ID hoặc source_table.USER_ID.
    target = column_name.upper()
    for item in lookups:
        if item.get("name", "").upper() == target or item.get("source_table", "").upper() == target:
            return item
    return None


def values_as_options(values):
    return {f"{v['id_value']} - {v['display_value']}": v["id_value"] for v in values}
