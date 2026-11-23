"""Các thao tác metadata bảng/cột."""
import pandas as pd


def get_tables(client):
    return client.table("tables_meta").select("*").order("table_name").execute().data or []


def get_columns(client, table_id=None):
    query = client.table("columns_meta").select("*").order("column_name")
    if table_id is not None:
        query = query.eq("table_id", table_id)
    return query.execute().data or []


def create_table(client, payload):
    return client.table("tables_meta").insert(payload).execute().data[0]


def update_table(client, table_id, payload):
    return client.table("tables_meta").update(payload).eq("id", table_id).execute()


def delete_table(client, table_id):
    return client.table("tables_meta").delete().eq("id", table_id).execute()


def create_column(client, payload):
    return client.table("columns_meta").insert(payload).execute()


def delete_column(client, column_id):
    return client.table("columns_meta").delete().eq("id", column_id).execute()


def import_columns(client, table_id, file):
    df = pd.read_csv(file)
    required = {"column_name", "data_type"}
    if not required.issubset(df.columns):
        raise ValueError("CSV phải có cột: column_name, data_type")
    rows = [{"table_id": table_id, "column_name": str(r.column_name).upper(),
             "data_type": str(r.data_type).upper()} for r in df.itertuples()]
    if rows:
        client.table("columns_meta").insert(rows).execute()


def import_schema_csv(client, file, user_id):
    """Import toàn bộ schema từ CSV: table_name,column_name,data_type,..."""
    df = pd.read_csv(file).fillna("")
    required = {"table_name", "column_name", "data_type"}
    if not required.issubset(df.columns):
        raise ValueError("CSV phải có header: table_name,column_name,data_type")
    df["table_name"] = df["table_name"].astype(str).str.strip().str.upper()
    df["column_name"] = df["column_name"].astype(str).str.strip().str.upper()
    df["data_type"] = df["data_type"].astype(str).str.strip().str.upper()
    table_map = {row["table_name"]: row["id"] for row in get_tables(client)}
    for table_name in df["table_name"].unique():
        if table_name not in table_map:
            created = create_table(client, {"table_name": table_name, "created_by": user_id})
            table_map[table_name] = created["id"]
    # Upsert cho phép chạy lại file mà không tạo trùng bảng/cột.
    rows = []
    for record in df.to_dict("records"):
        def as_bool(value): return str(value).strip().lower() in ("1", "true", "yes", "y", "x")
        rows.append({"table_id": table_map[record["table_name"]], "column_name": record["column_name"],
                     "data_type": record["data_type"], "is_primary_key": as_bool(record.get("is_primary_key", "")),
        "is_lookup_column": as_bool(record.get("is_lookup_column", "")), "is_nullable": as_bool(record.get("is_nullable", "true")),
        "has_default": as_bool(record.get("has_default", "")),
                     "description": str(record.get("description", ""))})
    if rows:
        client.table("columns_meta").upsert(rows, on_conflict="table_id,column_name").execute()
    return len(table_map), len(rows)


def export_tables_csv(client):
    tables = get_tables(client)
    return pd.DataFrame(tables).to_csv(index=False).encode("utf-8-sig")


def set_tables_group(client, table_names, group_name, color=None):
    """Gán danh sách bảng vào một nhóm và gán màu sắc hiển thị."""
    payload = {"group_name": group_name.strip() if group_name and group_name.strip() else None}
    if color:
        payload["color"] = color
    for name in table_names:
        client.table("tables_meta").update(payload).eq("table_name", name).execute()


def update_group(client, old_group_name, new_group_name, new_color=None, included_tables=None):
    """Đổi tên/màu nhóm và cập nhật danh sách các bảng thuộc nhóm."""
    target_name = new_group_name.strip() if new_group_name and new_group_name.strip() else None
    payload = {"group_name": target_name}
    if new_color:
        payload["color"] = new_color

    if included_tables is not None:
        included_set = set(included_tables)
        curr_tables = client.table("tables_meta").select("table_name").eq("group_name", old_group_name).execute().data or []
        curr_set = {t["table_name"] for t in curr_tables}
        # Những bảng trước đây thuộc nhóm nhưng nay bị bỏ chọn -> gỡ nhóm
        to_remove = curr_set - included_set
        for name in to_remove:
            client.table("tables_meta").update({"group_name": None}).eq("table_name", name).execute()
        # Những bảng trong included_set -> cập nhật nhóm và màu
        for name in included_tables:
            client.table("tables_meta").update(payload).eq("table_name", name).execute()
    else:
        client.table("tables_meta").update(payload).eq("group_name", old_group_name).execute()


def delete_group(client, group_name):
    """Xóa nhóm: đặt group_name = None cho toàn bộ các bảng trong nhóm."""
    return client.table("tables_meta").update({"group_name": None}).eq("group_name", group_name).execute()

