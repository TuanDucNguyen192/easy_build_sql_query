"""Tab trực quan hoá quan hệ các bảng Oracle và quản lý nhóm bảng."""
import pandas as pd
import streamlit as st

from core.erd_builder import (
    DEFAULT_COLOR,
    filter_graph,
    generate_table_join_sql,
    normalize_selection,
    related_table_names,
    table_description,
)
from db import relations_repo, tables_repo

try:
    from streamlit_agraph import Config, Edge, Node, agraph
except ModuleNotFoundError:
    Config = Edge = Node = agraph = None


def _show_details(client, tables_by_name, relations, table_name):
    table = tables_by_name.get(table_name)
    if not table:
        st.info("Chọn một bảng trên sơ đồ để xem chi tiết.")
        return
    st.subheader(f"📋 {table_name}")

    # Hiển thị nhóm và nút đổi nhóm nhanh
    curr_group = table.get("group_name") or "Chưa phân nhóm"
    curr_color = table.get("color") or DEFAULT_COLOR

    col_grp_info, col_grp_btn = st.columns([3, 1])
    with col_grp_info:
        st.markdown(
            f"Nhóm: <span style='background-color:{curr_color}; color:white; padding:3px 10px; border-radius:12px; font-weight:600; font-size:13px;'>{curr_group}</span>",
            unsafe_allow_html=True,
        )
    with col_grp_btn:
        with st.popover("🏷️ Đổi", use_container_width=True):
            existing_groups = sorted({t.get("group_name") for t in tables_by_name.values() if t.get("group_name")})
            pop_mode = st.radio("Thao tác:", ["Chọn nhóm có sẵn", "Tạo nhóm mới", "Gỡ khỏi nhóm"], key=f"pop_mode_{table_name}")
            if pop_mode == "Chọn nhóm có sẵn":
                if existing_groups:
                    target_g = st.selectbox("Chọn nhóm", existing_groups, key=f"pop_sel_{table_name}")
                    g_color = next((t.get("color") for t in tables_by_name.values() if t.get("group_name") == target_g and t.get("color")), curr_color)
                    if st.button("Lưu nhóm", key=f"pop_save_{table_name}", type="primary", use_container_width=True):
                        tables_repo.set_tables_group(client, [table_name], target_g, g_color)
                        st.toast(f"Đã chuyển bảng vào nhóm '{target_g}'")
                        st.rerun()
                else:
                    st.info("Chưa có nhóm nào. Vui lòng chọn 'Tạo nhóm mới'.")
            elif pop_mode == "Tạo nhóm mới":
                new_g = st.text_input("Tên nhóm mới", key=f"pop_new_{table_name}")
                new_c = st.color_picker("Màu nhóm", value=curr_color, key=f"pop_color_{table_name}")
                if st.button("Tạo & Gán nhóm", key=f"pop_create_{table_name}", type="primary", use_container_width=True):
                    if new_g.strip():
                        tables_repo.set_tables_group(client, [table_name], new_g.strip(), new_c)
                        st.toast(f"Đã gán nhóm '{new_g.strip()}'")
                        st.rerun()
                    else:
                        st.warning("Vui lòng nhập tên nhóm.")
            else:
                if st.button("Xác nhận gỡ nhóm", key=f"pop_remove_{table_name}", type="secondary", use_container_width=True):
                    tables_repo.set_tables_group(client, [table_name], None)
                    st.toast("Đã gỡ bảng khỏi nhóm")
                    st.rerun()

    st.write(table_description(table))

    # Danh sách cột
    columns = tables_repo.get_columns(client, table["id"])
    frame = pd.DataFrame([{
        "Cột": column["column_name"], "Kiểu": column.get("data_type", ""),
        "PK": "✓" if column.get("is_primary_key") else "",
        "Lookup": "✓" if column.get("is_lookup_column") else "",
        "Note": column.get("note", ""),
    } for column in columns])
    st.dataframe(frame, use_container_width=True, hide_index=True)

    st.markdown("**🔗 Bảng liên quan**")
    related = sorted(related_table_names(relations, table_name))
    if not related:
        st.caption("Chưa khai báo quan hệ.")
    for other in related:
        if st.button(f"→ {other}", key=f"erd_relation_{table_name}_{other}", use_container_width=True):
            st.session_state.selected_table_erd = other
            st.rerun()

    if st.button("🔍 Query bảng này", type="primary", use_container_width=True):
        st.session_state.query_table_from_erd = table["table_name"]
        st.success("Đã chọn bảng. Mở tab Query để tiếp tục.")

    # --- HIDDEN INFO SECTION ---
    with st.expander("🔒 Hidden Info: Tra cứu SQL & Cột liên quan", expanded=False):
        st.markdown("**1. Tên bảng SQL:**")
        st.code(table_name, language="sql")

        col_names = [c["column_name"] for c in columns]
        if col_names:
            st.markdown(f"**2. Danh sách tất cả cột ({len(col_names)} cột):**")
            cols_csv = ", ".join(col_names)
            st.text_area("Cột dạng CSV (tiện copy):", value=cols_csv, height=70, key=f"hidden_csv_{table_name}")
            cols_sql = ",\n       ".join([f"t1.{c}" for c in col_names])
            st.code(f"SELECT {cols_sql}\nFROM {table_name} t1;", language="sql")

        # Quan hệ chi tiết
        table_rels = [
            r for r in relations
            if r.get("source_table") == table_name or r.get("target_table") == table_name
        ]
        if table_rels:
            st.markdown("**3. Bảng & Cột liên kết SQL (Foreign Key / Relations):**")
            rel_rows = []
            for r in table_rels:
                is_src = r.get("source_table") == table_name
                other_t = r.get("target_table") if is_src else r.get("source_table")
                local_c = r.get("source_column") if is_src else r.get("target_column")
                other_c = r.get("target_column") if is_src else r.get("source_column")
                direction = "→" if is_src else "←"
                rel_rows.append({
                    "Cột bảng này": local_c or "ID",
                    "Liên kết": direction,
                    "Bảng liên quan": other_t,
                    "Cột bảng liên quan": other_c or "ID",
                    "Loại": r.get("relation_type", ""),
                    "Mô tả / Nhãn": r.get("description") or r.get("relation_label") or "",
                })
            st.dataframe(pd.DataFrame(rel_rows), use_container_width=True, hide_index=True)

            st.markdown("**4. Câu lệnh SQL JOIN mẫu để query trực tiếp DB:**")
            join_sql = generate_table_join_sql(table_name, relations)
            st.code(join_sql, language="sql")
        else:
            st.markdown("**3. Câu lệnh SQL SELECT mẫu:**")
            st.code(f"SELECT t1.*\nFROM {table_name} t1\nFETCH FIRST 100 ROWS ONLY;", language="sql")

        st.markdown("**5. Metadata kỹ thuật:**")
        st.json({
            "table_id": table.get("id"),
            "table_name": table.get("table_name"),
            "alias": table.get("alias"),
            "group_name": table.get("group_name"),
            "color": table.get("color"),
            "schema_name": table.get("schema_name"),
            "db_link": table.get("db_link"),
            "description_vi": table.get("description_vi"),
        })


def render(client):
    st.subheader("🗺️ Sơ đồ bảng")
    if agraph is None:
        st.error("Chưa cài streamlit-agraph. Chạy `pip install -r requirements.txt` rồi khởi động lại app.")
        return
    try:
        tables = tables_repo.get_tables(client)
        relations = relations_repo.get_relations(client)
    except Exception as exc:
        st.error("Chưa có dữ liệu sơ đồ. Admin hãy chạy file SQL migration mới trong Supabase SQL Editor.")
        st.caption(str(exc))
        return
    if not tables:
        st.info("Chưa có metadata bảng. Admin hãy import hoặc thêm bảng trước.")
        return

    tables_by_name = {table["table_name"]: table for table in tables}
    all_table_names = sorted(tables_by_name.keys())
    existing_groups = sorted({table.get("group_name") for table in tables if table.get("group_name")})

    # --- KHỐI QUẢN LÝ NHÓM BẢNG (THÊM / SỬA / XÓA) ---
    with st.expander("🏷️ Quản lý nhóm bảng (Thêm / Sửa / Xóa nhóm)", expanded=False):
        tab_add, tab_edit, tab_del = st.tabs(["➕ Thêm / Gán nhóm", "✏️ Sửa nhóm", "🗑️ Xóa nhóm"])

        # TAB 1: THÊM / GÁN NHÓM
        with tab_add:
            st.markdown("##### Tạo nhóm mới hoặc gán các bảng vào nhóm")
            add_mode = st.radio("Chế độ:", ["Tạo nhóm mới", "Gán vào nhóm đã có"], horizontal=True, key="add_grp_mode")
            if add_mode == "Tạo nhóm mới":
                col_name, col_color = st.columns([3, 1])
                new_grp_name = col_name.text_input("Tên nhóm mới", placeholder="Ví dụ: Đơn hàng, Kho vận, Rework...", key="new_grp_name")
                new_grp_color = col_color.color_picker("Màu đại diện nhóm", value="#3498DB", key="new_grp_color")
            else:
                if not existing_groups:
                    st.info("Chưa có nhóm nào. Vui lòng chọn 'Tạo nhóm mới'.")
                    new_grp_name = ""
                    new_grp_color = "#3498DB"
                else:
                    col_name, col_color = st.columns([3, 1])
                    new_grp_name = col_name.selectbox("Chọn nhóm có sẵn", existing_groups, key="add_exist_grp_name")
                    matched_color = next((t.get("color") for t in tables if t.get("group_name") == new_grp_name and t.get("color")), "#3498DB")
                    new_grp_color = col_color.color_picker("Màu nhóm", value=matched_color, key="add_exist_grp_color")

            selected_tables_to_add = st.multiselect("Chọn các bảng để gán vào nhóm này:", all_table_names, key="add_grp_tables_multi")

            if st.button("💾 Lưu và gán nhóm", type="primary", key="btn_save_new_group"):
                if not new_grp_name or not new_grp_name.strip():
                    st.warning("Vui lòng nhập hoặc chọn tên nhóm.")
                elif not selected_tables_to_add:
                    st.warning("Vui lòng chọn ít nhất một bảng.")
                else:
                    tables_repo.set_tables_group(client, selected_tables_to_add, new_grp_name.strip(), new_grp_color)
                    st.success(f"Đã gán {len(selected_tables_to_add)} bảng vào nhóm '{new_grp_name.strip()}'!")
                    st.rerun()

            with st.expander("🔒 Hidden Info: Lệnh SQL cập nhật nhóm tương ứng", expanded=False):
                if new_grp_name and selected_tables_to_add:
                    tbl_str = ", ".join([f"'{t}'" for t in selected_tables_to_add])
                    sql_preview = f"UPDATE public.tables_meta\nSET group_name = '{new_grp_name.strip()}', color = '{new_grp_color}'\nWHERE table_name IN ({tbl_str});"
                else:
                    sql_preview = "-- Chọn nhóm và bảng để xem câu lệnh SQL tương ứng"
                st.code(sql_preview, language="sql")

        # TAB 2: SỬA NHÓM
        with tab_edit:
            st.markdown("##### Đổi tên, đổi màu hoặc thay đổi danh sách bảng thuộc nhóm")
            if not existing_groups:
                st.info("Chưa có nhóm nào để sửa.")
            else:
                edit_grp = st.selectbox("Chọn nhóm cần sửa:", existing_groups, key="edit_grp_sel")
                curr_color = next((t.get("color") for t in tables if t.get("group_name") == edit_grp and t.get("color")), "#95A5A6")
                curr_tables_in_grp = sorted([t["table_name"] for t in tables if t.get("group_name") == edit_grp])

                ec1, ec2 = st.columns([3, 1])
                edited_name = ec1.text_input("Tên nhóm (có thể sửa đổi):", value=edit_grp, key=f"edit_grp_name_input_{edit_grp}")
                edited_color = ec2.color_picker("Màu đại diện mới:", value=curr_color, key=f"edit_grp_color_picker_{edit_grp}")

                edited_tables = st.multiselect("Danh sách bảng thuộc nhóm này:", all_table_names, default=curr_tables_in_grp, key=f"edit_grp_tables_multi_{edit_grp}")

                if st.button("💾 Cập nhật nhóm", type="primary", key="btn_update_group"):
                    if not edited_name or not edited_name.strip():
                        st.warning("Tên nhóm không được để trống.")
                    else:
                        tables_repo.update_group(client, edit_grp, edited_name.strip(), edited_color, edited_tables)
                        st.success(f"Đã cập nhật nhóm '{edited_name.strip()}' thành công!")
                        st.rerun()

                with st.expander("🔒 Hidden Info: Lệnh SQL cập nhật nhóm tương ứng", expanded=False):
                    tbl_str = ", ".join([f"'{t}'" for t in edited_tables]) if edited_tables else "''"
                    sql_preview = (
                        f"-- Cập nhật tên và màu mới cho các bảng trong nhóm:\n"
                        f"UPDATE public.tables_meta\nSET group_name = '{edited_name.strip()}', color = '{edited_color}'\nWHERE table_name IN ({tbl_str});\n\n"
                        f"-- Gỡ các bảng bị bỏ chọn khỏi nhóm:\n"
                        f"UPDATE public.tables_meta\nSET group_name = NULL\nWHERE group_name = '{edit_grp}' AND table_name NOT IN ({tbl_str});"
                    )
                    st.code(sql_preview, language="sql")

        # TAB 3: XÓA NHÓM
        with tab_del:
            st.markdown("##### Xóa nhóm bảng")
            if not existing_groups:
                st.info("Chưa có nhóm nào để xóa.")
            else:
                del_grp = st.selectbox("Chọn nhóm muốn xóa:", existing_groups, key="del_grp_sel")
                tables_in_del = [t["table_name"] for t in tables if t.get("group_name") == del_grp]
                st.warning(f"⚠️ Nhóm **'{del_grp}'** hiện đang có **{len(tables_in_del)}** bảng: {', '.join(tables_in_del[:8])}{'...' if len(tables_in_del) > 8 else ''}.\n\nKhi xóa nhóm, các bảng sẽ **không bị xóa** mà chỉ chuyển về trạng thái **Chưa phân nhóm**.")

                if st.button(f"🗑️ Xác nhận xóa nhóm '{del_grp}'", type="secondary", key="btn_del_group"):
                    tables_repo.delete_group(client, del_grp)
                    st.success(f"Đã xóa nhóm '{del_grp}'!")
                    st.rerun()

                with st.expander("🔒 Hidden Info: Lệnh SQL xóa nhóm tương ứng", expanded=False):
                    sql_preview = f"UPDATE public.tables_meta\nSET group_name = NULL\nWHERE group_name = '{del_grp}';"
                    st.code(sql_preview, language="sql")

    selected_name = st.session_state.get("selected_table_erd")
    if selected_name not in tables_by_name:
        selected_name = None
    groups = sorted({table.get("group_name") for table in tables if table.get("group_name")})
    top_left, top_middle, top_right = st.columns([2, 1, 1])
    search = top_left.text_input("Tìm bảng hoặc mô tả", placeholder="Ví dụ: G_WO_BASE, đơn hàng")
    group = top_middle.selectbox("Nhóm", ["Tất cả", *groups])
    mode = top_right.selectbox("Chế độ xem", ["Toàn bộ", "Liên quan trực tiếp", "Luồng Đơn hàng → WO → SN"], key="erd_mode")
    reset, zoom_in, zoom_out = st.columns(3)
    if reset.button("↺ Reset view"):
        st.session_state.pop("selected_table_erd", None)
        st.session_state.erd_zoom = 1.0
        st.rerun()
    if zoom_in.button("＋ Zoom in"):
        st.session_state.erd_zoom = min(st.session_state.get("erd_zoom", 1.0) + 0.2, 2.0)
        st.rerun()
    if zoom_out.button("－ Zoom out"):
        st.session_state.erd_zoom = max(st.session_state.get("erd_zoom", 1.0) - 0.2, 0.6)
        st.rerun()

    flow_names = {"G_DN_BASE", "G_WO_BASE", "G_WO_BOM", "G_SN_TRAVEL", "G_SN_KEYPARTS", "SYS_PART", "SYS_PROCESS", "SYS_MODEL", "SYS_TERMINAL"}
    if mode == "Luồng Đơn hàng → WO → SN":
        graph_tables = [table for table in tables if table["table_name"] in flow_names]
        names = {table["table_name"] for table in graph_tables}
        graph_relations = [relation for relation in relations if relation["source_table"] in names and relation["target_table"] in names]
    else:
        graph_tables, graph_relations = filter_graph(
            tables, relations, group, search, selected_name, mode == "Liên quan trực tiếp"
        )
    if not graph_tables:
        st.warning("Không có bảng phù hợp với bộ lọc hiện tại.")
        return
    query = search.strip().lower()
    zoom = st.session_state.get("erd_zoom", 1.0)
    nodes = [Node(
        id=table["table_name"],
        label=f"{table['table_name']}\n({table_description(table)[:45]})",
        size=(34 if query and (query in table["table_name"].lower() or query in table_description(table).lower()) else 25) * zoom,
        color=table.get("color") or DEFAULT_COLOR,
        shape="box",
        title=table_description(table),
    ) for table in graph_tables]
    edges = [Edge(
        source=relation["source_table"], target=relation["target_table"],
        label=relation.get("relation_label") or "", color="#BDC3C7",
    ) for relation in graph_relations]
    graph_column, detail_column = st.columns([7, 3])
    with graph_column:
        selected = agraph(
            nodes=nodes, edges=edges,
            config=Config(width=800, height=620, directed=True, physics=True,
                          nodeHighlightBehavior=True, highlightColor="#F1C40F", collapsible=False),
        )
        chosen = normalize_selection(selected)
        if chosen in tables_by_name:
            st.session_state.selected_table_erd = chosen
            selected_name = chosen
    with detail_column:
        _show_details(client, tables_by_name, relations, selected_name)
