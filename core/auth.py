"""Đăng nhập Supabase Auth và role của người dùng trong phiên hiện tại."""
from types import SimpleNamespace
import streamlit as st

DEFAULT_USER = SimpleNamespace(id=None, email="admin@local")


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


def auto_login(client):
    """Tự động đăng nhập ngầm vào Supabase hoặc khởi tạo phiên admin mặc định."""
    # 1. Khôi phục phiên đã có nếu người dùng thao tác trong cùng session
    user = restore_login(client)
    if user:
        return user

    # 2. Tự động đăng nhập ngầm nếu secrets.toml có cấu hình tài khoản
    email = st.secrets.get("AUTO_LOGIN_EMAIL") or st.secrets.get("DEFAULT_EMAIL")
    password = st.secrets.get("AUTO_LOGIN_PASSWORD") or st.secrets.get("DEFAULT_PASSWORD")
    if email and password:
        try:
            return login(client, str(email).strip(), str(password).strip())
        except Exception as exc:
            st.warning(f"Tự động đăng nhập Supabase thất bại ({email}): {exc}")

    # 3. Chế độ vào thẳng mặc định với quyền ADMIN
    st.session_state.user = DEFAULT_USER
    st.session_state.profile = {"id": None, "email": "admin@local", "role": "ADMIN"}
    return DEFAULT_USER


def logout(client):
    try:
        client.auth.sign_out()
    except Exception:
        pass
    finally:
        for key in ("user", "profile", "query_state", "auth_session"):
            st.session_state.pop(key, None)


def current_profile(client):
    user = st.session_state.get("user")
    if not user:
        return {"id": None, "email": "admin@local", "role": "ADMIN"}
    user_id = getattr(user, "id", None)
    if not user_id:
        return {"id": None, "email": getattr(user, "email", "admin@local"), "role": "ADMIN"}
    try:
        response = client.table("profiles").select("*").eq("id", user_id).execute().data
        return response[0] if response else {"id": user_id, "email": getattr(user, "email", ""), "role": "ADMIN"}
    except Exception:
        return {"id": user_id, "email": getattr(user, "email", ""), "role": "ADMIN"}


def is_admin():
    profile = st.session_state.get("profile")
    if not profile:
        return True
    return profile.get("role", "ADMIN") == "ADMIN"
