import streamlit as st
from core.auth import login


def render(client):
    st.title("Oracle Quick Query")
    st.caption("Tạo SQL Oracle bằng chuột — không chạy query, không cần Oracle Client.")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Đăng nhập", type="primary")
    if submitted:
        try:
            login(client, email, password)
            st.rerun()
        except Exception as exc:
            st.error(f"Đăng nhập thất bại: {exc}")
