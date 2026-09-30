import streamlit as st
import streamlit.components.v1 as components
from db import tables_repo, lookups_repo, history_repo
from core.update_builder import build_update_sql
from ui.value_widgets import render_value_input, render_where_conditions


def render(client):
    st.subheader("Update SQL")
    tables = tables_repo.get_tables(client)
    if not tables:
        st.info("Chưa có metadata bảng."); return
    table = st.selectbox("Bảng cần update", tables, format_func=lambda x: x["table_name"], key="update_table")
    columns, lookups = tables_repo.get_columns(client, table["id"]), lookups_repo.get_lookups(client)
    st.markdown("### SET — Cột cần cập nhật")
    count = st.session_state.get("update_set_count", 0)
    if st.button("+ Thêm cột", key="update_add_set"):
        st.session_state.update_set_count = count + 1; st.rerun()
    assignments = []
    for index in range(count):
        with st.container(border=True):
            a, b, c = st.columns([3, 4, 2])
            column = a.selectbox("Cột", columns, format_func=lambda x: x["column_name"], key=f"update_set_col_{index}")
            use_default = c.checkbox("Dùng DEFAULT", key=f"update_default_{index}")
            use_null = c.checkbox("NULL", key=f"update_null_{index}")
            value = "" if use_default or use_null else render_value_input(f"update_set_value_{index}", column, lookups, client, "Giá trị mới")
            assignments.append({"column": column, "value": value, "use_default": use_default, "use_null": use_null})
    if count > 0 and st.button("× Xóa cột cuối", key="update_remove_set"):
        st.session_state.update_set_count = count - 1; st.rerun()
    st.markdown("### WHERE — Điều kiện")
    conditions = render_where_conditions("update", columns, lookups, client)
    sql = build_update_sql(table["table_name"], assignments, conditions)
    if not conditions:
        st.error("⚠️ Không có điều kiện WHERE — sẽ update TOÀN BỘ bảng!")
    st.subheader("SQL Oracle"); st.code(sql, language="sql")
    understood = st.checkbox("Tôi hiểu rủi ro", key="update_understood", disabled=bool(conditions)) if not conditions else True
    copy, save = st.columns(2)
    if copy.button("📋 Copy SQL", key="copy_update", disabled=not understood):
        components.html(f"<script>navigator.clipboard.writeText({sql!r});</script>", height=0); st.toast("Đã copy vào clipboard")
    name = save.text_input("Tên query để lưu", key="update_history_name")
    if save.button("💾 Lưu vào lịch sử", key="save_update", disabled=not understood):
        if not name: st.warning("Nhập tên query trước khi lưu.")
        else: history_repo.save_history(client, name, {"table": table, "assignments": assignments, "conditions": conditions}, sql, st.session_state.user.id, "UPDATE"); st.success("Đã lưu vào lịch sử.")
