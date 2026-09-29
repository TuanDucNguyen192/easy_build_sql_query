"""CRUD lookup và các giá trị hiển thị."""
import pandas as pd


def get_lookups(client):
    return client.table("lookups").select("*").order("name").execute().data or []


def get_values(client, lookup_id):
    return client.table("lookup_values").select("*").eq("lookup_id", lookup_id).order("display_value").execute().data or []


def create_lookup(client, payload):
    return client.table("lookups").insert(payload).execute().data[0]


def delete_lookup(client, lookup_id):
    return client.table("lookups").delete().eq("id", lookup_id).execute()


def add_value(client, payload):
    return client.table("lookup_values").upsert(payload, on_conflict="lookup_id,id_value").execute()


def import_values(client, lookup_id, file):
    df = pd.read_csv(file)
    if not {"id", "display_value"}.issubset(df.columns):
        raise ValueError("CSV phải có cột: id, display_value")
    rows = [{"lookup_id": lookup_id, "id_value": str(r.id), "display_value": str(r.display_value)} for r in df.itertuples()]
    if rows:
        client.table("lookup_values").upsert(rows, on_conflict="lookup_id,id_value").execute()
