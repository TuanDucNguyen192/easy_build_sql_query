"""Quản lý Bảng & Cột: Thêm bảng mới, nhập nhiều cột từ SQL/File/Text, quản lý cột và schema."""
import pandas as pd
import streamlit as st

from core.schema_parser import parse_columns_file, parse_columns_text, parse_sql_insert
from db import tables_repo


def render(client):
    st.subheader("Quản lý Bảng & Cột")

    # Lấy danh sách bảng hiện có để dùng chung cho gợi ý nhóm và chọn bảng
    tables = tables_repo.get_tables(client)
    existing_groups = sorted({t.get("group_name") for t in tables if t.get("group_name")})

    # =========================================================================
    # KHỐI 1: THÊM BẢNG MỚI (HỖ TRỢ DÁN SQL, FORM & NHẬP NHIỀU CỘT)
    # =========================================================================
    with st.expander("➕ Nhập bảng mới (Dán câu lệnh SQL hoặc nhập Form & nhiều cột)", expanded=not bool(tables)):
        tab_sql, tab_form = st.tabs(["⚡ Dán câu lệnh SQL INSERT", "📝 Nhập theo Form & Nhiều cột"])

        # ---------------------------------------------------------------------
        # TAB 1: DÁN CÂU LỆNH SQL INSERT (TRỰC TIẾP NHƯ TRONG YÊU CẦU)
        # ---------------------------------------------------------------------
        with tab_sql:
            st.caption("Dán trực tiếp câu lệnh `INSERT INTO tables_meta...` và `INSERT INTO columns_meta...`. Hệ thống sẽ tự động bóc tách thông tin bảng và các cột.")
            default_placeholder = (
                "INSERT INTO tables_meta (\n"
                "    table_name, alias, description, schema_name, db_link, description_vi, search_keywords\n"
                ") VALUES (\n"
                "    'G_PACK_CARTON', 'Pack Carton', 'Bảng lưu thông tin đóng gói carton', 'SAJET', NULL,\n"
                "    'Bảng lưu thông tin đóng gói carton', 'Carton, đóng gói, pack, G_PACK_CARTON'\n"
                ");\n\n"
                "INSERT INTO columns_meta (table_id, column_name, data_type, is_primary_key, is_lookup_column, description) VALUES\n"
                "(54, 'PRODUCT', 'VARCHAR', FALSE, FALSE, 'Tên sản phẩm'),\n"
                "(54, 'SN', 'VARCHAR', FALSE, TRUE, 'Số serial number của máy'),\n"
                "(54, 'TEST_STATION_NAME', 'VARCHAR', FALSE, TRUE, 'Tên trạm test'),\n"
                "(54, 'STATION_ID', 'VARCHAR', FALSE, TRUE, 'ID trạm test'),\n"
                "(54, 'SW_VERSION', 'VARCHAR', FALSE, FALSE, 'Phiên bản phần mềm');"
            )
            sql_text = st.text_area("Dán script SQL INSERT vào đây:", height=220, placeholder=default_placeholder, key="sql_insert_input")

            if sql_text.strip():
                parsed = parse_sql_insert(sql_text)
                tbl_info = parsed.get("table")
                cols_info = parsed.get("columns", [])

                if tbl_info:
                    st.markdown("##### 🔍 Kết quả phân tích SQL:")
                    col_t1, col_t2 = st.columns([2, 3])
                    with col_t1:
                        st.markdown(f"**Bảng:** `{tbl_info.get('table_name', '')}`")
                        st.markdown(f"**Schema:** `{tbl_info.get('schema_name', '') or 'Mặc định'}`")
                        st.markdown(f"**Alias:** `{tbl_info.get('alias', '') or 'Không có'}`")
                    with col_t2:
                        st.markdown(f"**Mô tả:** {tbl_info.get('description_vi') or tbl_info.get('description') or 'Không có'}")
                        st.markdown(f"**Từ khóa:** {tbl_info.get('search_keywords', '') or 'Không có'}")

                    if cols_info:
                        st.markdown(f"**Danh sách cột trích xuất được ({len(cols_info)} cột):**")
                        df_preview = pd.DataFrame([{
                            "Tên cột": c["column_name"],
                            "Kiểu dữ liệu": c["data_type"],
                            "Khóa chính (PK)": "✓" if c["is_primary_key"] else "",
                            "Lookup": "✓" if c["is_lookup_column"] else "",
                            "Mô tả": c["description"],
                        } for c in cols_info])
                        st.dataframe(df_preview, use_container_width=True, hide_index=True)
                    else:
                        st.info("Chưa tìm thấy câu lệnh `INSERT INTO columns_meta` trong script trên. Nếu bạn chỉ muốn tạo bảng thì bấm Lưu bên dưới.")

                    if st.button("💾 Xác nhận lưu bảng và toàn bộ cột vào Database", type="primary", key="btn_save_sql_insert"):
                        try:
                            user_id = getattr(st.session_state.get("user"), "id", None)
                            tbl_info["created_by"] = user_id
                            created_tbl = tables_repo.create_or_update_table(client, tbl_info)
                            table_id = created_tbl["id"]
                            col_count = tables_repo.batch_create_columns(client, table_id, cols_info)
                            st.success(f"🎉 Đã lưu thành công bảng **{created_tbl['table_name']}** với **{col_count}** cột!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Lỗi khi lưu bảng vào Database: {exc}")
                else:
                    st.warning("Chưa nhận diện được cú pháp `INSERT INTO tables_meta (...) VALUES (...)`. Hãy kiểm tra lại câu lệnh SQL.")

        # ---------------------------------------------------------------------
        # TAB 2: NHẬP THEO FORM VÀ NHẬP NHIỀU CỘT (CSV / EXCEL / TEXT / EDITOR)
        # ---------------------------------------------------------------------
        with tab_form:
            st.markdown("##### 1. Thông tin bảng")
            fc1, fc2, fc3 = st.columns([2, 1, 1])
            form_tbl_name = fc1.text_input("Tên bảng Oracle *", placeholder="Ví dụ: G_PACK_CARTON", key="form_tbl_name").upper().strip()
            form_schema = fc2.text_input("Schema", placeholder="Ví dụ: SAJET", key="form_schema").strip()
            form_dblink = fc3.text_input("DB Link", placeholder="Ví dụ: DBLINK_NAME", key="form_dblink").strip()

            fc4, fc5 = st.columns([2, 2])
            form_alias = fc4.text_input("Alias gợi ý", placeholder="Ví dụ: Pack Carton", key="form_alias").strip()
            # Chọn nhóm có sẵn hoặc nhập mới
            grp_choices = ["(Chưa phân nhóm)", "+ Nhập nhóm mới...", *existing_groups]
            chosen_grp = fc5.selectbox("Nhóm bảng", grp_choices, key="form_grp_choice")
            if chosen_grp == "+ Nhập nhóm mới...":
                form_group_name = st.text_input("Tên nhóm mới:", placeholder="Ví dụ: Đóng gói / Carton", key="form_new_grp_text").strip()
            elif chosen_grp == "(Chưa phân nhóm)":
                form_group_name = None
            else:
                form_group_name = chosen_grp

            fc6, fc7 = st.columns(2)
            form_desc_vi = fc6.text_input("Mô tả tiếng Việt", placeholder="Ví dụ: Bảng lưu thông tin đóng gói carton", key="form_desc_vi").strip()
            form_desc = fc7.text_input("Mô tả chi tiết / English", placeholder="Ví dụ: Carton packing information", key="form_desc").strip()
            form_keywords = st.text_input("Từ khóa tìm kiếm (search keywords)", placeholder="Ví dụ: Carton, đóng gói, pack, G_PACK_CARTON", key="form_keywords").strip()

            st.divider()
            st.markdown("##### 2. Nhập danh sách cột (nhiều cột cùng lúc)")
            col_input_mode = st.radio(
                "Phương thức nhập cột:",
                ["📋 Dán văn bản (Text / CSV / TSV / SQL VALUES)", "📁 Tải lên file (CSV / Excel)", "✍️ Nhập trên bảng tương tác"],
                horizontal=True,
                key="form_col_mode",
            )

            columns_to_save = []

            if col_input_mode == "📋 Dán văn bản (Text / CSV / TSV / SQL VALUES)":
                st.caption(
                    "Hỗ trợ: **CSV** (`PRODUCT, VARCHAR, false, false, Tên sản phẩm`) "
                    "hoặc **Copy từ Excel** (tab) "
                    "hoặc **SQL VALUES** (`(54, 'PRODUCT', 'VARCHAR', FALSE, FALSE, 'Tên sản phẩm'), ...`)"
                )
                text_cols = st.text_area(
                    "Dán danh sách cột vào đây:",
                    height=160,
                    placeholder=(
                        "PRODUCT, VARCHAR, FALSE, FALSE, Tên sản phẩm\n"
                        "SN, VARCHAR, FALSE, TRUE, Số serial number của máy\n"
                        "TEST_STATION_NAME, VARCHAR, FALSE, TRUE, Tên trạm test\n"
                        "STATION_ID, VARCHAR, FALSE, TRUE, ID trạm test\n"
                        "SW_VERSION, VARCHAR, FALSE, FALSE, Phiên bản phần mềm"
                    ),
                    key="form_text_cols_input",
                )
                if text_cols.strip():
                    columns_to_save = parse_columns_text(text_cols)

            elif col_input_mode == "📁 Tải lên file (CSV / Excel)":
                st.caption("File cần có cột `column_name` và `data_type`. Tuỳ chọn: `is_primary_key`, `is_lookup_column`, `description`.")
                file_up = st.file_uploader("Chọn file CSV hoặc Excel (.xlsx, .xls):", type=["csv", "xlsx", "xls"], key="form_col_file")
                if file_up:
                    try:
                        columns_to_save = parse_columns_file(file_up)
                    except Exception as e:
                        st.error(f"Lỗi khi đọc file: {e}")

            else:  # Bảng tương tác data_editor
                st.caption("Chỉnh sửa trực tiếp hoặc bấm nút `+` bên dưới bảng để thêm dòng mới:")
                init_data = pd.DataFrame([
                    {"column_name": "PRODUCT", "data_type": "VARCHAR2", "is_primary_key": False, "is_lookup_column": False, "description": "Tên sản phẩm"},
                    {"column_name": "SN", "data_type": "VARCHAR2", "is_primary_key": False, "is_lookup_column": True, "description": "Số serial number"},
                ])
                edited_df = st.data_editor(
                    init_data,
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "column_name": st.column_config.TextColumn("Tên cột *", required=True),
                        "data_type": st.column_config.SelectboxColumn("Kiểu dữ liệu", options=["VARCHAR2", "NUMBER", "DATE", "TIMESTAMP", "CLOB"], default="VARCHAR2", required=True),
                        "is_primary_key": st.column_config.CheckboxColumn("PK (Khóa chính)", default=False),
                        "is_lookup_column": st.column_config.CheckboxColumn("Lookup", default=False),
                        "description": st.column_config.TextColumn("Mô tả cột"),
                    },
                    key="form_data_editor_cols",
                )
                columns_to_save = edited_df.to_dict("records")

            # Hiển thị preview các cột sẽ lưu
            if columns_to_save:
                st.markdown(f"**Xem trước danh sách cột ({len(columns_to_save)} cột):**")
                df_prev = pd.DataFrame([{
                    "Tên cột": c.get("column_name", ""),
                    "Kiểu dữ liệu": c.get("data_type", "VARCHAR2"),
                    "PK": "✓" if c.get("is_primary_key") else "",
                    "Lookup": "✓" if c.get("is_lookup_column") else "",
                    "Mô tả": c.get("description", ""),
                } for c in columns_to_save if str(c.get("column_name", "")).strip()])
                st.dataframe(df_prev, use_container_width=True, hide_index=True)

            if st.button("💾 Lưu bảng và toàn bộ danh sách cột", type="primary", key="btn_save_form_table"):
                if not form_tbl_name:
                    st.warning("Vui lòng nhập Tên bảng Oracle.")
                else:
                    try:
                        user_id = getattr(st.session_state.get("user"), "id", None)
                        tbl_payload = {
                            "table_name": form_tbl_name,
                            "alias": form_alias or None,
                            "schema_name": form_schema or None,
                            "db_link": form_dblink or None,
                            "group_name": form_group_name,
                            "description": form_desc or None,
                            "description_vi": form_desc_vi or form_desc or None,
                            "search_keywords": form_keywords or None,
                            "created_by": user_id,
                        }
                        created_tbl = tables_repo.create_or_update_table(client, tbl_payload)
                        table_id = created_tbl["id"]
                        valid_cols = [c for c in columns_to_save if str(c.get("column_name", "")).strip()]
                        col_count = tables_repo.batch_create_columns(client, table_id, valid_cols)
                        st.success(f"🎉 Đã lưu thành công bảng **{created_tbl['table_name']}** với **{col_count}** cột!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi khi lưu bảng: {exc}")

    # =========================================================================
    # KHỐI 2: IMPORT TOÀN BỘ SCHEMA TỪ CSV (GIỮ TÍNH NĂNG CŨ)
    # =========================================================================
    with st.expander("📁 Import toàn bộ schema (Nhiều bảng & cột từ một CSV)", expanded=False):
        st.caption("Header bắt buộc: `table_name,column_name,data_type`. Tuỳ chọn: `is_primary_key,is_lookup_column,description`")
        schema_file = st.file_uploader("CSV toàn bộ bảng/cột", type="csv", key="schema_csv")
        if schema_file and st.button("Import schema", type="primary"):
            try:
                user_id = getattr(st.session_state.get("user"), "id", None)
                table_count, column_count = tables_repo.import_schema_csv(client, schema_file, user_id)
                st.success(f"Đã import {column_count} cột thuộc {table_count} bảng.")
                st.rerun()
            except Exception as exc:
                st.error(f"Import thất bại: {exc}")

    # =========================================================================
    # KHỐI 3: QUẢN LÝ BẢNG & CỘT HIỆN CÓ
    # =========================================================================
    st.divider()
    col_dl1, col_dl2 = st.columns([3, 1])
    with col_dl1:
        st.subheader("📋 Danh sách Bảng & Quản lý Cột")
    with col_dl2:
        st.download_button("📥 Tải backup bảng CSV", tables_repo.export_tables_csv(client), "tables_backup.csv", "text/csv", use_container_width=True)

    if not tables:
        st.info("Chưa có bảng nào trong Database. Hãy nhập bảng mới ở khối phía trên.")
        return

    # Lựa chọn bảng cần quản lý
    selected = st.selectbox(
        "Chọn bảng để xem và quản lý cột:",
        tables,
        format_func=lambda x: f"{x['table_name']}{' (' + (x.get('description_vi') or x.get('description') or x.get('alias') or '') + ')' if (x.get('description_vi') or x.get('description') or x.get('alias')) else ''}",
        key="manage_selected_table",
    )
    cols = tables_repo.get_columns(client, selected["id"])

    # Hiển thị thông tin bảng đang chọn
    st.caption(
        f"**Tên bảng:** `{selected['table_name']}` · "
        f"**Nhóm:** {selected.get('group_name') or 'Chưa phân nhóm'} · "
        f"**Schema:** {selected.get('schema_name') or 'Mặc định'} · "
        f"**Tổng số cột:** {len(cols)}"
    )
    st.dataframe(cols, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # NHẬP THÊM NHIỀU CỘT CHO BẢNG ĐANG CHỌN (BATCH ADD COLUMNS)
    # -------------------------------------------------------------------------
    with st.expander(f"📥 Nhập thêm nhiều cột cho bảng '{selected['table_name']}' (Dán text / File CSV & Excel)", expanded=False):
        batch_col_mode = st.radio(
            "Chọn cách nhập:",
            ["Dán văn bản (Text / CSV / TSV / SQL VALUES)", "Tải lên file (CSV / Excel)"],
            horizontal=True,
            key=f"batch_col_mode_{selected['id']}",
        )
        batch_columns = []
        if "Dán văn bản" in batch_col_mode:
            batch_text = st.text_area(
                "Dán danh sách cột vào đây:",
                height=150,
                placeholder=(
                    "COLUMN_NAME_1, VARCHAR2, FALSE, FALSE, Mô tả cột 1\n"
                    "COLUMN_NAME_2, NUMBER, TRUE, FALSE, Khóa chính\n"
                    "(54, 'COLUMN_NAME_3', 'VARCHAR', FALSE, TRUE, 'Mô tả cột 3')"
                ),
                key=f"batch_text_{selected['id']}",
            )
            if batch_text.strip():
                batch_columns = parse_columns_text(batch_text)
        else:
            batch_file = st.file_uploader("Chọn file CSV hoặc Excel:", type=["csv", "xlsx", "xls"], key=f"batch_file_{selected['id']}")
            if batch_file:
                try:
                    batch_columns = parse_columns_file(batch_file)
                except Exception as e:
                    st.error(f"Lỗi đọc file: {e}")

        if batch_columns:
            st.markdown(f"**Xem trước các cột sẽ thêm vào '{selected['table_name']}' ({len(batch_columns)} cột):**")
            df_b_prev = pd.DataFrame([{
                "Tên cột": c["column_name"],
                "Kiểu dữ liệu": c["data_type"],
                "PK": "✓" if c["is_primary_key"] else "",
                "Lookup": "✓" if c["is_lookup_column"] else "",
                "Mô tả": c["description"],
            } for c in batch_columns])
            st.dataframe(df_b_prev, use_container_width=True, hide_index=True)

            if st.button(f"💾 Thêm {len(batch_columns)} cột vào bảng '{selected['table_name']}'", type="primary", key=f"btn_save_batch_cols_{selected['id']}"):
                try:
                    added_count = tables_repo.batch_create_columns(client, selected["id"], batch_columns)
                    st.success(f"Đã thêm thành công {added_count} cột vào bảng '{selected['table_name']}'!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Lỗi khi thêm cột: {exc}")

    # -------------------------------------------------------------------------
    # THÊM 1 CỘT ĐƠN LẺ (NHƯ CŨ)
    # -------------------------------------------------------------------------
    with st.expander(f"➕ Thêm 1 cột lẻ vào bảng '{selected['table_name']}'", expanded=False):
        with st.form("new_column"):
            a, b, c = st.columns(3)
            col_name = a.text_input("Tên cột").upper().strip()
            data_type = b.selectbox("Kiểu", ["VARCHAR2", "NUMBER", "DATE", "TIMESTAMP", "CLOB", "CHAR"])
            pk = c.checkbox("Khóa chính (PK)")
            is_lookup = c.checkbox("Cột dùng lookup")
            nullable = c.checkbox("Cho phép NULL", value=True)
            has_default = c.checkbox("Có DEFAULT")
            description = st.text_input("Mô tả cột")
            if st.form_submit_button("Thêm cột", type="primary"):
                if col_name:
                    tables_repo.create_column(client, {
                        "table_id": selected["id"],
                        "column_name": col_name,
                        "data_type": data_type,
                        "is_primary_key": pk,
                        "is_lookup_column": is_lookup,
                        "is_nullable": nullable,
                        "has_default": has_default,
                        "description": description,
                    })
                    st.success(f"Đã thêm cột '{col_name}'")
                    st.rerun()
                else:
                    st.warning("Vui lòng nhập tên cột.")

    # -------------------------------------------------------------------------
    # XÓA CỘT HOẶC XÓA TOÀN BỘ BẢNG
    # -------------------------------------------------------------------------
    st.divider()
    col_del_c, col_del_t = st.columns(2)
    with col_del_c:
        if cols:
            delete_col = st.selectbox("Xóa một cột:", cols, format_func=lambda x: f"{x['column_name']} ({x.get('data_type', '')})", key="delete_col_select")
            if st.button("🗑️ Xóa cột đã chọn", type="secondary", key="btn_del_col"):
                tables_repo.delete_column(client, delete_col["id"])
                st.success(f"Đã xóa cột '{delete_col['column_name']}'")
                st.rerun()
    with col_del_t:
        st.write("")
        st.write("")
        if st.button(f"🗑️ Xóa toàn bộ bảng '{selected['table_name']}'", type="secondary", key="btn_del_full_table"):
            tables_repo.delete_table(client, selected["id"])
            st.success(f"Đã xóa bảng '{selected['table_name']}'!")
            st.rerun()
