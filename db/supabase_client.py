"""Khởi tạo Supabase an toàn từ Streamlit secrets."""
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_client():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as exc:
        raise RuntimeError("Không thể kết nối Supabase. Hãy kiểm tra secrets.") from exc
