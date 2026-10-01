"""Giao diện web cho chức năng SQL IN-List Converter."""
import streamlit as st
import streamlit.components.v1 as components
from core.sql_in_list import convert_to_sql_in_list


def render():
    st.subheader("SQL IN-List Converter")
    st.caption("Dán các mã cách nhau bằng khoảng trắng, tab hoặc xuống dòng để chuyển thành Oracle IN (...).")
    source = st.text_area("Danh sách mã nguồn", placeholder="Ví dụ:\nA8F5E1FFD437\na8f5e1ffd438 A8:F5:E1:FF:D4:39", height=190, key="in_list_source")
    sql_in_list, count = convert_to_sql_in_list(source)
    a, b = st.columns([1, 5])
    a.metric("Số lượng mã", count)
    if b.button("📋 Copy IN-list", type="primary", disabled=not sql_in_list):
        components.html(f"<script>navigator.clipboard.writeText({sql_in_list!r});</script>", height=0)
        st.toast("Đã copy IN-list vào clipboard")
    st.code(sql_in_list or "-- Dán danh sách mã để xem kết quả", language="sql")
    if st.button("Xóa danh sách"):
        st.session_state.in_list_source = ""
        st.rerun()
