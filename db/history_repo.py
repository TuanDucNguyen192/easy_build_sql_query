"""Lịch sử query được lưu tập trung trong Supabase."""

def list_history(client):
    # created_by ban đầu tham chiếu auth.users. Không join profiles trực tiếp vì
    # PostgREST chỉ tự nhận diện quan hệ foreign key trong cùng schema public.
    # Lấy lịch sử trước để không làm hỏng toàn bộ tab khi schema chưa nâng cấp.
    rows = client.table("query_history").select("*").order("created_at", desc=True).execute().data or []
    profile_rows = client.table("profiles").select("id,email").execute().data or []
    emails = {row["id"]: row.get("email", "") for row in profile_rows}
    for row in rows:
        row["creator_email"] = emails.get(row.get("created_by"), "")
    return rows


def save_history(client, name, state, sql, user_id, query_type="SELECT"):
    return client.table("query_history").insert({"name": name, "state_json": state, "sql_text": sql, "created_by": user_id, "query_type": query_type}).execute()


def delete_history(client, history_id):
    return client.table("query_history").delete().eq("id", history_id).execute()
