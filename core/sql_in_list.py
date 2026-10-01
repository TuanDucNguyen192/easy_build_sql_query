"""Chuyển danh sách mã thành biểu thức SQL IN cho Oracle."""


def convert_to_sql_in_list(text: str) -> tuple[str, int]:
    """Tách theo mọi khoảng trắng, giữ thứ tự và quote giá trị an toàn cho SQL."""
    tokens = (text or "").split()
    if not tokens:
        return "", 0
    values = ", ".join("'" + token.replace("'", "''") + "'" for token in tokens)
    return f"({values})", len(tokens)
