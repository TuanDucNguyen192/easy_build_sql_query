"""Parser hỗ trợ nhập bảng và danh sách cột từ SQL, CSV, TSV hoặc text."""
import io
import re
import pandas as pd


def _clean_token(token):
    token = token.strip()
    upper = token.upper()
    if upper == "NULL" or not token:
        return None
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False
    if (token.startswith("'") and token.endswith("'")) or (token.startswith('"') and token.endswith('"')):
        # Bỏ quote ngoài cùng và unescape '' -> '
        val = token[1:-1]
        return val.replace("''", "'")
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        return token


def _split_sql_row(row_str):
    """Tách các giá trị trong một tuple (val1, val2, ...) có tính đến nháy đơn/kép."""
    tokens = []
    current = []
    in_quote = False
    quote_char = ""
    i = 0
    n = len(row_str)
    while i < n:
        ch = row_str[i]
        if ch in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = ch
                current.append(ch)
            elif quote_char == ch:
                # Kiểm tra escape '' trong SQL
                if i + 1 < n and row_str[i + 1] == ch:
                    current.append(ch)
                    current.append(ch)
                    i += 1
                else:
                    in_quote = False
                    current.append(ch)
            else:
                current.append(ch)
        elif ch == "," and not in_quote:
            tokens.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    if current:
        tokens.append("".join(current).strip())
    return [_clean_token(t) for t in tokens]


def parse_sql_insert(sql_text):
    """Trích xuất metadata bảng và các cột từ câu lệnh SQL INSERT.
    
    Hỗ trợ cú pháp:
      INSERT INTO tables_meta (...) VALUES (...);
      INSERT INTO columns_meta (...) VALUES (...), (...);
    """
    result = {"table": None, "columns": []}
    if not sql_text or not sql_text.strip():
        return result

    # 1. Parse tables_meta
    table_pattern = re.compile(
        r"INSERT\s+INTO\s+(?:public\.)?tables_meta\s*\((.*?)\)\s*VALUES\s*\((.*?)\)",
        re.IGNORECASE | re.DOTALL,
    )
    table_match = table_pattern.search(sql_text)
    if table_match:
        cols = [c.strip().lower() for c in table_match.group(1).split(",")]
        vals = _split_sql_row(table_match.group(2))
        table_dict = {}
        for col, val in zip(cols, vals):
            if val is not None:
                table_dict[col] = val
        result["table"] = table_dict

    # 2. Parse columns_meta
    col_pattern = re.compile(
        r"INSERT\s+INTO\s+(?:public\.)?columns_meta\s*\((.*?)\)\s*VALUES\s*(.*)",
        re.IGNORECASE | re.DOTALL,
    )
    col_match = col_pattern.search(sql_text)
    if col_match:
        target_cols = [c.strip().lower() for c in col_match.group(1).split(",")]
        raw_values = col_match.group(2).strip()
        # Tìm tất cả các cụm (val1, val2, ...)
        row_matches = re.finditer(r"\((.*?)\)", raw_values, re.DOTALL)
        for rm in row_matches:
            vals = _split_sql_row(rm.group(1))
            col_data = {}
            for col_name, val in zip(target_cols, vals):
                if col_name != "table_id":  # Bỏ qua table_id cũ trong SQL
                    col_data[col_name] = val
            if col_data.get("column_name"):
                result["columns"].append(_normalize_column_dict(col_data))

    return result


def _normalize_column_dict(data):
    """Chuẩn hóa dict cột để đảm bảo các trường bắt buộc có giá trị hợp lệ."""
    c_name = str(data.get("column_name") or "").strip().upper()
    d_type = str(data.get("data_type") or "VARCHAR2").strip().upper()
    if d_type in ("VARCHAR", "VARCHAR2", "CHAR", "NVARCHAR2"):
        d_type = "VARCHAR2"
    elif d_type in ("INT", "INTEGER", "NUMBER", "FLOAT", "DOUBLE"):
        d_type = "NUMBER"

    def _to_bool(v):
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "t", "yes", "y", "✓", "x")

    return {
        "column_name": c_name,
        "data_type": d_type,
        "is_primary_key": _to_bool(data.get("is_primary_key")),
        "is_lookup_column": _to_bool(data.get("is_lookup_column")),
        "description": str(data.get("description") or "").strip(),
        "note": str(data.get("note") or "").strip(),
    }


def parse_columns_text(text):
    """Parse text nhiều dòng chứa danh sách cột.
    
    Hỗ trợ:
      1. SQL tuples: (54, 'PRODUCT', 'VARCHAR', FALSE, FALSE, 'Tên sản phẩm'),
      2. CSV: PRODUCT, VARCHAR, FALSE, FALSE, Tên sản phẩm
      3. TSV (Copy từ Excel): PRODUCT\tVARCHAR\tFALSE\tFALSE\tTên sản phẩm
      4. Space: PRODUCT VARCHAR2 Tên sản phẩm
    """
    rows = []
    if not text or not text.strip():
        return rows

    # Thử parse dạng SQL INSERT trước nếu có từ khóa
    if "INSERT INTO" in text.upper():
        res = parse_sql_insert(text)
        if res["columns"]:
            return res["columns"]

    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for line in lines:
        line = line.rstrip(",;").strip()
        if not line:
            continue
        # Dạng SQL tuple: (..., ...)
        if line.startswith("(") and line.endswith(")"):
            inner = line[1:-1]
            tokens = _split_sql_row(inner)
            # Nếu phần tử đầu là số (table_id), bỏ qua
            if tokens and isinstance(tokens[0], int) and len(tokens) >= 3:
                tokens = tokens[1:]
            if tokens:
                c_data = {
                    "column_name": tokens[0] if len(tokens) > 0 else "",
                    "data_type": tokens[1] if len(tokens) > 1 else "VARCHAR2",
                    "is_primary_key": tokens[2] if len(tokens) > 2 else False,
                    "is_lookup_column": tokens[3] if len(tokens) > 3 else False,
                    "description": tokens[4] if len(tokens) > 4 else "",
                    "note": tokens[5] if len(tokens) > 5 else "",
                }
                if c_data["column_name"]:
                    rows.append(_normalize_column_dict(c_data))
            continue

        # Dạng TSV (tab)
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        # Dạng CSV (phẩy)
        elif "," in line:
            parts = _split_sql_row(line)
        # Dạng space
        else:
            parts = line.split(maxsplit=2)

        if not parts or not parts[0]:
            continue

        c_data = {
            "column_name": parts[0],
            "data_type": parts[1] if len(parts) > 1 else "VARCHAR2",
            "is_primary_key": parts[2] if len(parts) > 2 else False,
            "is_lookup_column": parts[3] if len(parts) > 3 else False,
            "description": parts[4] if len(parts) > 4 else "",
            "note": parts[5] if len(parts) > 5 else "",
        }
        rows.append(_normalize_column_dict(c_data))

    return rows


def parse_columns_file(uploaded_file):
    """Đọc file CSV hoặc Excel và chuyển thành danh sách dict các cột."""
    filename = uploaded_file.name.lower()
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(uploaded_file).fillna("")
    else:
        # CSV
        df = pd.read_csv(uploaded_file).fillna("")

    # Map các tên header thường gặp về chuẩn
    header_map = {}
    for col in df.columns:
        norm = str(col).strip().lower().replace(" ", "_")
        if norm in ("column_name", "column", "ten_cot", "tên_cột", "cot", "cột", "name"):
            header_map[col] = "column_name"
        elif norm in ("data_type", "type", "kieu", "kiểu", "datatype", "kieu_du_lieu"):
            header_map[col] = "data_type"
        elif norm in ("is_primary_key", "is_pk", "pk", "primary_key", "khoa_chinh", "khóa_chính"):
            header_map[col] = "is_primary_key"
        elif norm in ("is_lookup_column", "is_lookup", "lookup", "lookup_column"):
            header_map[col] = "is_lookup_column"
        elif norm in ("description", "desc", "mo_ta", "mô_tả", "dien_giai", "diễn_giải"):
            header_map[col] = "description"
        elif norm in ("note", "ghi_chu", "ghi_chú"):
            header_map[col] = "note"

    df = df.rename(columns=header_map)
    if "column_name" not in df.columns:
        # Nếu không có header khớp, lấy cột đầu làm column_name, cột 2 làm data_type nếu có
        cols = list(df.columns)
        if cols:
            df = df.rename(columns={cols[0]: "column_name"})
            if len(cols) > 1:
                df = df.rename(columns={cols[1]: "data_type"})

    results = []
    for rec in df.to_dict("records"):
        if str(rec.get("column_name", "")).strip():
            results.append(_normalize_column_dict(rec))
    return results
