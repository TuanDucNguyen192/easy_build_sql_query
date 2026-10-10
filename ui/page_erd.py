"""Tab trực quan hoá quan hệ các bảng Oracle."""
import pandas as pd
import streamlit as st

from core.erd_builder import DEFAULT_COLOR, filter_graph, normalize_selection, related_table_names, table_description
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
    st.caption(table.get("group_name") or "Chưa phân nhóm")
    st.write(table_description(table))
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
