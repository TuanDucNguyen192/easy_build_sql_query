"""Đăng nhập Supabase Auth và role của người dùng trong phiên hiện tại."""
import streamlit as st

def restore_login(client):
    """Khôi phục client sau các lần rerun, không lưu token vào cookie/browser."""
    session = st.session_state.get("auth_session")
    if not session:
        return st.session_state.get("user")
    try:
        result = client.auth.set_session(session["access_token"], session["refresh_token"])
        st.session_state.user = result.user
        st.session_state.auth_session = {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
        }
        return result.user
    except Exception:
        for key in ("user", "profile", "auth_session"):
            st.session_state.pop(key, None)
        return None


def login(client, email, password):
    result = client.auth.sign_in_with_password({"email": email, "password": password})
    st.session_state.user = result.user
    # session_state thuộc riêng tab hiện tại và bị xóa khi người dùng F5.
    st.session_state.auth_session = {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }
    return result.user


def logout(client):
    try:
        client.auth.sign_out()
    finally:
        for key in ("user", "profile", "query_state", "auth_session"):
            st.session_state.pop(key, None)


def current_profile(client):
    user = st.session_state.get("user")
    if not user:
        return None
    response = client.table("profiles").select("*").eq("id", user.id).execute().data
    return response[0] if response else {"id": user.id, "email": user.email, "role": "USER"}


def is_admin():
    return st.session_state.get("profile", {}).get("role") == "ADMIN"
