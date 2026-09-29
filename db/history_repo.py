"""Lịch sử query được lưu tập trung trong Supabase."""

def list_history(client):
    return client.table("query_history").select("*,profiles(email)").order("created_at", desc=True).execute().data or []


def save_history(client, name, state, sql, user_id):
    return client.table("query_history").insert({"name": name, "state_json": state, "sql_text": sql, "created_by": user_id}).execute()


def delete_history(client, history_id):
    return client.table("query_history").delete().eq("id", history_id).execute()
