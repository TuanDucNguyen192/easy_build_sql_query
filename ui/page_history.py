import streamlit as st
from db import history_repo
from core.auth import is_admin


def render(client):
    st.subheader("Lịch sử query dùng chung")
    search = st.text_input("Tìm theo tên")
    rows = history_repo.list_history(client)
    rows = [r for r in rows if search.lower() in (r.get("name") or "").lower()]
    for row in rows:
        with st.expander(f"{row.get('name', 'Không tên')} · {row.get('creator_email', '')} · {str(row.get('created_at', ''))[:16]}"):
            st.code(row["sql_text"], language="sql")
            a, b = st.columns(2)
            if a.button("Nạp query", key=f"load{row['id']}"):
                st.session_state.query_state = row["state_json"]; st.success("Đã nạp. Mở tab Query.")
            if (is_admin() or row.get("created_by") == st.session_state.user.id) and b.button("Xóa", key=f"del{row['id']}"):
                history_repo.delete_history(client, row["id"]); st.rerun()
