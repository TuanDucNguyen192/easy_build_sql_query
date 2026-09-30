import streamlit as st
import streamlit.components.v1 as components
from db import tables_repo, lookups_repo, history_repo
from core.insert_builder import build_insert_sql
from ui.value_widgets import render_value_input


def _row_inputs(row_index, columns, lookups, client):
    items, missing_required = [], []
    st.markdown(f"#### Dòng {row_index + 1}")
    for col in columns:
        with st.container(border=True):
            head, flags = st.columns([3, 2])
            required = not col.get("is_nullable", True)
            head.markdown(f"{'🔴 ' if required else ''}**{col['column_name']}**  ")
            head.caption(col.get("data_type", "") + (" · DEFAULT" if col.get("has_default") else ""))
            # Cột đã được chọn ở đầu trang, không cần checkbox bỏ từng cột.
            skip = False
            if col.get("is_primary_key"):
                skip = flags.checkbox("Auto (sequence/trigger)", key=f"insert_auto_{row_index}_{col['id']}", value=True) or skip
            use_default = col.get("has_default", False) and flags.checkbox("Dùng DEFAULT", key=f"insert_default_{row_index}_{col['id']}")
            use_null = flags.checkbox("NULL", key=f"insert_null_{row_index}_{col['id']}")
            value = "" if (skip or use_default or use_null) else render_value_input(f"insert_{row_index}_{col['id']}", col, lookups, client, "Giá trị")
            if required and not skip and not use_default and not use_null and value == "":
                missing_required.append(col["column_name"])
            items.append({"column": col, "value": value, "skip": skip, "use_default": use_default, "use_null": use_null})
    return items, missing_required


def render(client):
    st.subheader("Insert SQL")
    tables = tables_repo.get_tables(client)
    if not tables:
        st.info("Chưa có metadata bảng."); return
    table = st.selectbox("Bảng cần insert", tables, format_func=lambda x: x["table_name"], key="insert_table")
    columns, lookups = tables_repo.get_columns(client, table["id"]), lookups_repo.get_lookups(client)
    selected_names = st.multiselect("Các cột cần insert", [col["column_name"] for col in columns],
                                    placeholder="Chọn các cột cần ghi dữ liệu", key=f"insert_columns_{table['id']}")
    columns = [col for col in columns if col["column_name"] in selected_names]
    if not columns:
        st.info("Chọn ít nhất một cột để bắt đầu nhập dữ liệu.")
        return
    row_count = st.session_state.get("insert_row_count", 1)
    rows, missing = [], []
    for index in range(row_count):
        row, required = _row_inputs(index, columns, lookups, client)
        rows.append(row); missing.extend(f"Dòng {index + 1}: {name}" for name in required)
    add, remove = st.columns(2)
    if add.button("+ Thêm dòng"):
        st.session_state.insert_row_count = row_count + 1; st.rerun()
    if row_count > 1 and remove.button("× Xóa dòng cuối"):
        st.session_state.insert_row_count = row_count - 1; st.rerun()
    version = st.selectbox("Phiên bản Oracle", ["19c (nhiều câu INSERT)", "23c+ (multi-row VALUES)"], key="insert_oracle_version")
    sql = build_insert_sql(table["table_name"], rows, "23c" if version.startswith("23") else "19c")
    if missing:
        st.warning("Thiếu giá trị cho cột bắt buộc: " + ", ".join(missing))
    st.subheader("SQL Oracle"); st.code(sql, language="sql")
    copy, save = st.columns(2)
    if copy.button("📋 Copy SQL", key="copy_insert"):
        components.html(f"<script>navigator.clipboard.writeText({sql!r});</script>", height=0); st.toast("Đã copy vào clipboard")
    name = save.text_input("Tên query để lưu", key="insert_history_name")
    if save.button("💾 Lưu vào lịch sử", key="save_insert"):
        if not name: st.warning("Nhập tên query trước khi lưu.")
        else: history_repo.save_history(client, name, {"table": table, "rows": rows}, sql, st.session_state.user.id, "INSERT"); st.success("Đã lưu vào lịch sử.")
