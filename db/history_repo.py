"""Lịch sử query được lưu tập trung trong Supabase."""


def _missing_column(exc, fields):
    """Trả về cột chưa có trên database cũ, nếu PostgREST báo PGRST204."""
    if getattr(exc, "code", None) != "PGRST204":
        return None
    message = str(exc)
    return next((field for field in fields if field in message), None)

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


def save_history(client, name, state, sql, user_id, query_type="SELECT", note=""):
    """Lưu lịch sử và trả về các cột migration còn thiếu (nếu có)."""
    payload = {"name": name, "state_json": state, "sql_text": sql, "created_by": user_id,
               "query_type": query_type, "note": note}
    missing_columns = set()
    while True:
        try:
            client.table("query_history").insert(payload).execute()
            return missing_columns
        except Exception as exc:
            missing = _missing_column(exc, payload.keys())
            if not missing:
                raise
            # Tương thích database chưa chạy migration; vẫn giữ được SQL cốt lõi.
            payload.pop(missing)
            missing_columns.add(missing)


def delete_history(client, history_id):
    return client.table("query_history").delete().eq("id", history_id).execute()
