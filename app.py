import streamlit as st
from db.supabase_client import get_client
from core.auth import current_profile, logout, is_admin
from ui import page_login, page_query, page_tables, page_lookups, page_history

st.set_page_config(page_title="Oracle Quick Query", page_icon="⚡", layout="wide")

try:
    client = get_client()
except RuntimeError as exc:
    # st.stop() chỉ dừng khi file được chạy bởi Streamlit. SystemExit cũng
    # ngăn lỗi NameError nếu ai đó lỡ chạy `python app.py` trong terminal.
    st.error(str(exc))
    st.stop()
    raise SystemExit(1)

if not st.session_state.get("user"):
    page_login.render(client); st.stop()

try:
    st.session_state.profile = current_profile(client)
except Exception as exc:
    st.error(f"Không tải được quyền người dùng: {exc}"); st.stop()

with st.sidebar:
    st.write(f"**{st.session_state.profile.get('email', '')}**")
    st.caption(f"Role: {st.session_state.profile.get('role', 'USER')}")
    if st.button("Đăng xuất"):
        logout(client); st.rerun()

tabs = ["Query"] + (["Bảng & Cột", "Lookup"] if is_admin() else []) + ["Lịch sử"]
selected = st.tabs(tabs)
with selected[0]: page_query.render(client)
i = 1
if is_admin():
    with selected[i]: page_tables.render(client)
    i += 1
    with selected[i]: page_lookups.render(client)
    i += 1
with selected[i]: page_history.render(client)
# py -m streamlit run app.py