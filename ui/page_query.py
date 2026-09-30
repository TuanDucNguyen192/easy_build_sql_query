import streamlit as st
import streamlit.components.v1 as components
try:
    from streamlit_sortables import sort_items
except ModuleNotFoundError:
    # Không chặn toàn bộ ứng dụng khi máy chủ chưa cài dependency mới.
    sort_items = None
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
    lookup = lookup_for_column(col["column_name"], lookups)
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


def _time_condition(all_columns):
    date_columns = [x for x in all_columns if x[1].get("data_type", "").upper().startswith(("DATE", "TIMESTAMP"))]
    if not st.checkbox("Thêm điều kiện thời gian", key="use_time_filter"):
        return None
    if not date_columns:
        st.warning("Không có cột DATE/TIMESTAMP để lọc thời gian.")
        return None
    choice = st.selectbox("Cột thời gian", date_columns, format_func=lambda x: x[0], key="time_column")
    preset = st.selectbox("Khoảng thời gian", ["Hôm nay", "Hôm qua", "7 ngày gần nhất", "30 ngày gần nhất", "Tháng này", "Tháng trước", "Tùy chọn"], key="time_preset")
    if preset == "Tùy chọn":
        return {"ref": choice[0], "op": "BETWEEN", "value": str(st.date_input("Từ ngày", key="time_start")), "value2": str(st.date_input("Đến ngày", key="time_end")), "data_type": choice[1].get("data_type")}
    expressions = {
        "Hôm nay": ("TRUNC(SYSDATE)", "TRUNC(SYSDATE) + 1"), "Hôm qua": ("TRUNC(SYSDATE) - 1", "TRUNC(SYSDATE)"),
        "7 ngày gần nhất": ("TRUNC(SYSDATE) - 6", "TRUNC(SYSDATE) + 1"), "30 ngày gần nhất": ("TRUNC(SYSDATE) - 29", "TRUNC(SYSDATE) + 1"),
        "Tháng này": ("TRUNC(SYSDATE, 'MM')", "ADD_MONTHS(TRUNC(SYSDATE, 'MM'), 1)"), "Tháng trước": ("ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)", "TRUNC(SYSDATE, 'MM')"),
    }
    start, end = expressions[preset]
    return {"ref": choice[0], "op": "RANGE_EXCLUSIVE_END", "value": start, "value2": end, "data_type": choice[1].get("data_type")}


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
        st.caption("Chọn SELECT * hoặc các cột riêng lẻ.")
        select_all_main = st.checkbox("SELECT * (toàn bộ cột bảng chính)", key="select_all_main")
        selected_names = st.multiselect("Các cột hiển thị", [c["column_name"] for c in main_cols], default=[c["column_name"] for c in main_cols], key=f"selected_columns_{main['id']}", disabled=select_all_main)
        ordered_names = selected_names
        if selected_names:
            # Popover giữ giao diện Query gọn; danh sách kéo-thả chỉ hiện khi cần đổi thứ tự.
            with st.popover("↕ Sắp xếp vị trí cột", use_container_width=True):
                if sort_items:
                    ordered_names = sort_items(selected_names, direction="vertical", key=f"column_order_{main['id']}")
                else:
                    st.info("Cài `pip install -r requirements.txt` để bật kéo-thả thứ tự cột.")
        selected = [next(c for c in main_cols if c["column_name"] == name) for name in ordered_names]
        link_count = st.number_input("Số bảng link (JOIN)", 0, 5, 0, step=1)
        links = []
        for i in range(int(link_count)):
            with st.expander(f"Link bảng {i + 1}", expanded=True):
                choices = [t for t in tables if t["id"] != main["id"]]
                join_table = st.selectbox("Bảng cần link", choices, format_func=lambda x:x["table_name"], key=f"jt{i}")
                join_cols = tables_repo.get_columns(client, join_table["id"])
                join_type = st.selectbox("Loại JOIN", ["LEFT JOIN", "INNER JOIN", "RIGHT JOIN", "FULL OUTER JOIN", "CROSS JOIN"], key=f"jtype{i}")
                suggest_l, suggest_r = _suggest(main_cols, join_cols)
                left_col = st.selectbox("Cột nối bảng chính", main_cols, index=main_cols.index(suggest_l), format_func=lambda x:x["column_name"], key=f"jl{i}", disabled=join_type == "CROSS JOIN")
                right_col = st.selectbox("Cột nối bảng link", join_cols, index=join_cols.index(suggest_r), format_func=lambda x:x["column_name"], key=f"jr{i}", disabled=join_type == "CROSS JOIN")
                names = st.multiselect("Cột lấy thêm", [c["column_name"] for c in join_cols], key=f"jc{i}")
                links.append({"table": join_table, "join_type": join_type, "left": left_col, "right": right_col, "selected": [c for c in join_cols if c["column_name"] in names]})
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
        time_condition = _time_condition(all_columns)
        if time_condition:
            conditions.append(time_condition)
        limit = st.selectbox("Số lượng", [10, 50, 100, 500, 1000, "Tất cả"])
        order_choice = st.selectbox("Sắp xếp", ["Không sắp xếp"] + [x[0] for x in all_columns])
        direction = st.selectbox("Chiều sắp xếp", ["ASC", "DESC"])
    state = {"main": main, "selected": selected, "select_all_main": select_all_main, "links": links, "conditions": conditions, "limit": limit,
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
