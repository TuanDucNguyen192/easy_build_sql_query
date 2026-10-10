"""CRUD quan hệ giữa các bảng Oracle để hiển thị sơ đồ."""


def get_relations(client):
    return client.table("table_relations").select("*").order("source_table").execute().data or []


def get_relations_for_table(client, table_name):
    return (client.table("table_relations").select("*")
            .or_(f"source_table.eq.{table_name},target_table.eq.{table_name}")
            .execute().data or [])


def create_relation(client, payload):
    return client.table("table_relations").insert(payload).execute().data[0]


def update_relation(client, relation_id, payload):
    return client.table("table_relations").update(payload).eq("id", relation_id).execute()


def delete_relation(client, relation_id):
    return client.table("table_relations").delete().eq("id", relation_id).execute()
