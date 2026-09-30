"""Widget nhập giá trị và WHERE dùng chung giữa các tab."""
import streamlit as st
from db import lookups_repo
from core.lookup_helper import lookup_for_column, values_as_options


def render_value_input(key, column, lookups, client, label="Giá trị"):
    lookup = lookup_for_column(column["column_name"], lookups)
    if lookup:
        options = values_as_options(lookups_repo.get_values(client, lookup["id"]))
        if options:
            selected = st.selectbox(label, list(options), key=f"{key}_lookup")
            return options[selected]
    dtype = column.get("data_type", "").upper()
    if dtype.startswith(("DATE", "TIMESTAMP")):
        return str(st.date_input(label, key=f"{key}_date"))
    if dtype.startswith("CLOB"):
        return st.text_area(label, key=f"{key}_text")
    return st.text_input(label, key=f"{key}_text")


def render_where_conditions(key_prefix, columns, lookups, client):
    count_key = f"{key_prefix}_condition_count"
    if count_key not in st.session_state:
        st.session_state[count_key] = 0
    if st.button("+ Thêm điều kiện", key=f"{key_prefix}_add_condition"):
        st.session_state[count_key] += 1
    conditions, ops = [], ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN", "BETWEEN", "IS NULL", "IS NOT NULL"]
    for index in range(st.session_state[count_key]):
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([3, 2, 4])
            column = col_a.selectbox("Cột", columns, format_func=lambda x: x["column_name"], key=f"{key_prefix}_where_col_{index}")
            op = col_b.selectbox("Toán tử", ops, key=f"{key_prefix}_where_op_{index}")
            if op in ("IS NULL", "IS NOT NULL"):
                value = value2 = None
            elif op == "BETWEEN":
                dtype = column.get("data_type", "").upper()
                if dtype.startswith(("DATE", "TIMESTAMP")):
                    value = str(col_c.date_input("Từ ngày", key=f"{key_prefix}_where_value_{index}"))
                    value2 = str(col_c.date_input("Đến ngày", key=f"{key_prefix}_where_value2_{index}"))
                else:
                    value = col_c.text_input("Từ", key=f"{key_prefix}_where_value_{index}")
                    value2 = col_c.text_input("Đến", key=f"{key_prefix}_where_value2_{index}")
            else:
                value, value2 = render_value_input(f"{key_prefix}_where_value_{index}", column, lookups, client), None
            conditions.append({"ref": column["column_name"], "op": op, "value": value, "value2": value2, "data_type": column.get("data_type")})
    return conditions
