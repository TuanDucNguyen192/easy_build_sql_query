"""Định dạng giá trị thành literal Oracle, dùng chung cho INSERT/UPDATE/WHERE."""


def format_value_for_oracle(value, data_type, use_default=False, use_null=False):
    if use_default:
        return "DEFAULT"
    if use_null or value is None or str(value).upper() == "NULL":
        return "NULL"
    dtype = str(data_type or "").upper()
    if dtype.startswith(("DATE", "TIMESTAMP")):
        return "TO_DATE('" + str(value).replace("'", "''") + "', 'YYYY-MM-DD')"
    if dtype.startswith(("NUMBER", "INTEGER", "DECIMAL", "FLOAT", "BINARY_FLOAT", "BINARY_DOUBLE")):
        return str(value).strip()
    return "'" + str(value).replace("'", "''") + "'"
