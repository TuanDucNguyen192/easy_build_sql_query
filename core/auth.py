"""Đăng nhập Supabase Auth và role của người dùng."""
import streamlit as st


def login(client, email, password):
    result = client.auth.sign_in_with_password({"email": email, "password": password})
    st.session_state.user = result.user
    return result.user


def logout(client):
    client.auth.sign_out()
    for key in ("user", "profile", "query_state"):
        st.session_state.pop(key, None)


def current_profile(client):
    user = st.session_state.get("user")
    if not user:
        return None
    response = client.table("profiles").select("*").eq("id", user.id).execute().data
    return response[0] if response else {"id": user.id, "email": user.email, "role": "USER"}


def is_admin():
    return st.session_state.get("profile", {}).get("role") == "ADMIN"
