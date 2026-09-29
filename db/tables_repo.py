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


def export_tables_csv(client):
    tables = get_tables(client)
    return pd.DataFrame(tables).to_csv(index=False).encode("utf-8-sig")
