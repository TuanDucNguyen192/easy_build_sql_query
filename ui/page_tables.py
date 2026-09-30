import streamlit as st
from db import tables_repo


def render(client):
    st.subheader("Quản lý Bảng & Cột")
    with st.expander("Import toàn bộ schema từ một CSV", expanded=False):
        st.caption("Header bắt buộc: table_name,column_name,data_type. Tuỳ chọn: is_primary_key,is_lookup_column,description")
        schema_file = st.file_uploader("CSV toàn bộ bảng/cột", type="csv", key="schema_csv")
        if schema_file and st.button("Import schema", type="primary"):
            try:
                table_count, column_count = tables_repo.import_schema_csv(client, schema_file, st.session_state.user.id)
                st.success(f"Đã import {column_count} cột thuộc {table_count} bảng.")
                st.rerun()
            except Exception as exc:
                st.error(f"Import thất bại: {exc}")
    with st.expander("+ Thêm bảng", expanded=False):
        with st.form("new_table"):
            name = st.text_input("Tên bảng Oracle").upper()
            alias = st.text_input("Alias gợi ý (tuỳ chọn)")
            desc = st.text_input("Mô tả")
            if st.form_submit_button("Lưu bảng"):
                try:
                    tables_repo.create_table(client, {"table_name": name, "alias": alias, "description": desc, "created_by": st.session_state.user.id})
                    st.success("Đã thêm bảng"); st.rerun()
                except Exception as exc: st.error(str(exc))
    tables = tables_repo.get_tables(client)
    st.download_button("Tải backup bảng CSV", tables_repo.export_tables_csv(client), "tables_backup.csv", "text/csv")
    if not tables:
        st.info("Chưa có bảng nào."); return
    selected = st.selectbox("Chọn bảng để quản lý cột", tables, format_func=lambda x: x["table_name"])
    cols = tables_repo.get_columns(client, selected["id"])
    st.dataframe(cols, use_container_width=True, hide_index=True)
    with st.form("new_column"):
        a, b, c = st.columns(3)
        col_name = a.text_input("Tên cột").upper()
        data_type = b.selectbox("Kiểu", ["NUMBER", "VARCHAR2", "DATE", "TIMESTAMP", "CLOB"])
        pk = c.checkbox("Khóa chính")
        is_lookup = c.checkbox("Cột dùng lookup")
        nullable = c.checkbox("Cho phép NULL", value=True)
        has_default = c.checkbox("Có DEFAULT")
        description = st.text_input("Mô tả cột")
        if st.form_submit_button("Thêm cột"):
            tables_repo.create_column(client, {"table_id": selected["id"], "column_name": col_name, "data_type": data_type, "is_primary_key": pk, "is_lookup_column": is_lookup, "is_nullable": nullable, "has_default": has_default, "description": description})
            st.rerun()
    upload = st.file_uploader("Import cột từ CSV (column_name,data_type)", type="csv")
    if upload and st.button("Import CSV cột"):
        try: tables_repo.import_columns(client, selected["id"], upload); st.success("Đã import"); st.rerun()
        except Exception as exc: st.error(str(exc))
    if cols:
        delete = st.selectbox("Xóa cột", cols, format_func=lambda x: x["column_name"], key="delete_col")
        if st.button("Xóa cột đã chọn"):
            tables_repo.delete_column(client, delete["id"]); st.rerun()
    if st.button("Xóa toàn bộ bảng đang chọn", type="secondary"):
        tables_repo.delete_table(client, selected["id"]); st.rerun()
