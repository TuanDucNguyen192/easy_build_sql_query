import streamlit as st
from db import lookups_repo


def render(client):
    st.subheader("Quản lý Lookup (ID → Tên)")
    with st.expander("+ Tạo lookup"):
        with st.form("create_lookup"):
            name = st.text_input("Tên / cột áp dụng, ví dụ USER_ID").upper()
            source = st.text_input("Bảng nguồn, ví dụ USERS").upper()
            id_col, name_col = st.columns(2)
            id_column = id_col.text_input("Cột ID", value="ID").upper()
            name_column = name_col.text_input("Cột tên", value="NAME").upper()
            if st.form_submit_button("Lưu lookup"):
                lookups_repo.create_lookup(client, {"name": name, "source_table": source, "id_column": id_column, "name_column": name_column})
                st.rerun()
    lookups = lookups_repo.get_lookups(client)
    if not lookups: st.info("Chưa có lookup."); return
    lookup = st.selectbox("Chọn lookup", lookups, format_func=lambda x: x["name"])
    st.dataframe(lookups_repo.get_values(client, lookup["id"]), use_container_width=True, hide_index=True)
    with st.form("add_lookup_value"):
        a, b = st.columns(2); id_value = a.text_input("ID"); display = b.text_input("Tên hiển thị")
        if st.form_submit_button("Thêm / cập nhật giá trị"):
            lookups_repo.add_value(client, {"lookup_id": lookup["id"], "id_value": id_value, "display_value": display}); st.rerun()
    upload = st.file_uploader("Import CSV (id,display_value)", type="csv")
    if upload and st.button("Import CSV lookup"):
        try: lookups_repo.import_values(client, lookup["id"], upload); st.rerun()
        except Exception as exc: st.error(str(exc))
    if st.button("Xóa lookup này"):
        lookups_repo.delete_lookup(client, lookup["id"]); st.rerun()
