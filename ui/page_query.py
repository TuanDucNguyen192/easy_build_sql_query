import streamlit as st
import streamlit.components.v1 as components
from db import tables_repo, lookups_repo, history_repo
from core.sql_builder import build_sql
from core.lookup_helper import lookup_for_column, values_as_options


def _suggest(left_columns, right_columns):
    # USER_ID ↔ ID và ID ↔ USER_ID là hai gợi ý quan trọng nhất.
    for left in left_columns:
        for right in right_columns:
            if (left["column_name"], right["column_name"]) in (("USER_ID", "ID"), ("ID", "USER_ID")) or left["column_name"] == right["column_name"]:
                return left, right
    return left_columns[0], right_columns[0]


def _value_input(key, col, operator, lookups, client):
    if operator in ("IS NULL", "IS NOT NULL"): return None, None
    lookup = lookup_for_column(col["column_name"], lookups) if col.get("is_lookup_column") else None
    if lookup and operator not in ("IN", "BETWEEN"):
        opts = values_as_options(lookups_repo.get_values(client, lookup["id"]))
        label = st.selectbox("Giá trị", list(opts), key=f"val_{key}") if opts else st.text_input("Giá trị", key=f"val_{key}")
        return opts.get(label, label), None
    dtype = col.get("data_type", "").upper()
    if operator == "BETWEEN":
        if dtype.startswith("DATE"):
            return str(st.date_input("Từ ngày", key=f"val_{key}")), str(st.date_input("Đến ngày", key=f"val2_{key}"))
        return st.text_input("Từ", key=f"val_{key}"), st.text_input("Đến", key=f"val2_{key}")
    if dtype.startswith("DATE"):
        return str(st.date_input("Ngày", key=f"val_{key}")), None
    if dtype.startswith(("NUMBER", "INTEGER", "DECIMAL", "FLOAT")) and operator != "IN":
        return st.number_input("Giá trị", key=f"val_{key}"), None
    hint = "Nhập các giá trị cách nhau bằng dấu phẩy" if operator == "IN" else "Giá trị"
    return st.text_input(hint, key=f"val_{key}"), None


def render(client):
    st.subheader("Query Builder")
    if st.button("↻ Refresh data"):
        st.cache_data.clear(); st.rerun()
    tables = tables_repo.get_tables(client)
    if not tables: st.info("Chưa có metadata. Admin hãy thêm bảng và cột."); return
    state_saved = st.session_state.get("query_state", {})
    default_name = state_saved.get("main", {}).get("table_name")
    default_idx = next((i for i,t in enumerate(tables) if t["table_name"] == default_name), 0)
    left, right = st.columns(2)
    with left:
        main = st.selectbox("Bảng chính", tables, index=default_idx, format_func=lambda x: x["table_name"])
        main_cols = tables_repo.get_columns(client, main["id"])
        selected_names = st.multiselect("Cột hiển thị", [c["column_name"] for c in main_cols], default=[c["column_name"] for c in main_cols])
        selected = [c for c in main_cols if c["column_name"] in selected_names]
        link_count = st.number_input("Số bảng link (JOIN)", 0, 5, 0, step=1)
        links = []
        for i in range(int(link_count)):
            with st.expander(f"Link bảng {i + 1}", expanded=True):
                choices = [t for t in tables if t["id"] != main["id"]]
                join_table = st.selectbox("Bảng cần link", choices, format_func=lambda x:x["table_name"], key=f"jt{i}")
                join_cols = tables_repo.get_columns(client, join_table["id"])
                suggest_l, suggest_r = _suggest(main_cols, join_cols)
                left_col = st.selectbox("Cột nối bảng chính", main_cols, index=main_cols.index(suggest_l), format_func=lambda x:x["column_name"], key=f"jl{i}")
                right_col = st.selectbox("Cột nối bảng link", join_cols, index=join_cols.index(suggest_r), format_func=lambda x:x["column_name"], key=f"jr{i}")
                names = st.multiselect("Cột lấy thêm", [c["column_name"] for c in join_cols], key=f"jc{i}")
                links.append({"table": join_table, "left": left_col, "right": right_col, "selected": [c for c in join_cols if c["column_name"] in names]})
    with right:
        all_columns = [(f"t1.{c['column_name']}", c) for c in main_cols]
        for idx, link in enumerate(links, 2): all_columns += [(f"t{idx}.{c['column_name']}", c) for c in tables_repo.get_columns(client, link["table"]["id"])]
        lookups = lookups_repo.get_lookups(client)
        condition_count = st.number_input("Số điều kiện WHERE", 0, 10, 0, step=1)
        conditions = []
        ops = ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN", "BETWEEN", "IS NULL", "IS NOT NULL"]
        for i in range(int(condition_count)):
            with st.expander(f"Điều kiện {i+1}", expanded=True):
                choice = st.selectbox("Cột", all_columns, format_func=lambda x:x[0], key=f"condcol{i}")
                op = st.selectbox("Toán tử", ops, key=f"op{i}")
                value, value2 = _value_input(i, choice[1], op, lookups, client)
                conditions.append({"ref": choice[0], "op": op, "value": value, "value2": value2, "data_type": choice[1].get("data_type")})
        limit = st.selectbox("Số lượng", [10, 50, 100, 500, 1000, "Tất cả"])
        order_choice = st.selectbox("Sắp xếp", ["Không sắp xếp"] + [x[0] for x in all_columns])
        direction = st.selectbox("Chiều sắp xếp", ["ASC", "DESC"])
    state = {"main": main, "selected": selected, "links": links, "conditions": conditions, "limit": limit,
             "order": None if order_choice == "Không sắp xếp" else {"ref": order_choice, "direction": direction}}
    try: sql = build_sql(state)
    except Exception as exc: sql = f"-- Lỗi sinh SQL: {exc}"
    st.divider(); st.subheader("SQL Oracle")
    st.code(sql, language="sql")
    a, b = st.columns(2)
    if a.button("📋 Copy SQL", type="primary"):
        # Clipboard thuộc browser để hoạt động cả trên Streamlit Cloud.
        components.html(f"<script>navigator.clipboard.writeText({sql!r});</script>", height=0)
        st.toast("Đã copy vào clipboard")
    name = b.text_input("Tên query để lưu", placeholder="Ví dụ: Đơn hàng Active")
    if b.button("💾 Lưu query"):
        if not name: st.warning("Nhập tên query trước khi lưu.")
        else:
            history_repo.save_history(client, name, state, sql, st.session_state.user.id)
            st.success("Đã lưu vào lịch sử dùng chung.")
