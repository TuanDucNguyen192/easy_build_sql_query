"""Dịch vụ AI hỗ trợ truy vấn Database, sinh SQL Oracle và quản lý Schema Supabase."""
import streamlit as st
from openai import OpenAI

DEFAULT_PROVIDERS = {
    "DeepSeek": {
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "description": "DeepSeek API (mô hình deepseek-chat)",
    },
    "Groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "description": "Groq Cloud siêu tốc (Llama 3.3 70B)",
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "deepseek/deepseek-chat",
        "description": "OpenRouter (DeepSeek, Claude, GPT, Llama...)",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "description": "OpenAI API chính thức (GPT-4o-mini)",
    },
    "Tùy chỉnh (Custom)": {
        "base_url": "",
        "default_model": "",
        "description": "Tự nhập Base URL và Model của bạn",
    },
}


def get_ai_config():
    """Lấy cấu hình AI từ secrets hoặc session_state."""
    provider = (
        st.session_state.get("ai_provider")
        or st.secrets.get("AI_PROVIDER")
        or "DeepSeek"
    )
    preset = DEFAULT_PROVIDERS.get(provider, DEFAULT_PROVIDERS["DeepSeek"])

    api_key = (
        st.session_state.get("ai_api_key")
        or st.secrets.get("AI_API_KEY")
        or st.secrets.get("OPENAI_API_KEY")
        or st.secrets.get("DEEPSEEK_API_KEY")
        or st.secrets.get("GROQ_API_KEY")
        or ""
    )

    base_url = (
        st.session_state.get("ai_base_url")
        or st.secrets.get("AI_BASE_URL")
        or preset.get("base_url")
        or ""
    )

    model = (
        st.session_state.get("ai_model")
        or st.secrets.get("AI_MODEL")
        or preset.get("default_model")
        or "deepseek-chat"
    )

    return {
        "provider": provider,
        "api_key": api_key.strip(),
        "base_url": base_url.strip(),
        "model": model.strip(),
    }


@st.cache_data(ttl=180)
def build_schema_context(_client):
    """Trích xuất và tóm tắt toàn bộ schema metadata từ Supabase để nạp làm context cho AI."""
    try:
        tables = _client.table("tables_meta").select("*").order("table_name").execute().data or []
        # Lấy tối đa cột trong DB
        columns = _client.table("columns_meta").select("*").limit(3000).execute().data or []
        relations = _client.table("table_relations").select("*").execute().data or []
        lookups = _client.table("lookups").select("*").execute().data or []
    except Exception as exc:
        return f"Lỗi nạp schema metadata: {exc}"

    cols_by_table = {}
    for c in columns:
        tid = c.get("table_id")
        cols_by_table.setdefault(tid, []).append(c)

    lines = [
        "=== HỆ THỐNG METADATA CƠ SỞ DỮ LIỆU ORACLE (LƯU TRÊN SUPABASE) ===",
        f"Tổng số bảng: {len(tables)} bảng",
        "",
        "DANH SÁCH BẢNG VÀ CÁC CỘT:",
    ]

    for t in tables:
        tid = t.get("id")
        tname = t.get("table_name", "")
        alias = t.get("alias") or ""
        group = t.get("group_name") or "Chưa phân nhóm"
        desc = t.get("description_vi") or t.get("description") or ""
        schema = t.get("schema_name") or ""
        dblink = t.get("db_link") or ""

        header = f"- Bảng: {tname}"
        meta_tags = []
        if group:
            meta_tags.append(f"Nhóm: {group}")
        if desc:
            meta_tags.append(f"Mô tả: {desc}")
        if schema:
            meta_tags.append(f"Schema: {schema}")
        if dblink:
            meta_tags.append(f"DBLink: {dblink}")
        if meta_tags:
            header += f" [{', '.join(meta_tags)}]"
        lines.append(header)

        tcols = cols_by_table.get(tid, [])
        col_strs = []
        for c in tcols:
            cname = c.get("column_name", "")
            dtype = c.get("data_type", "")
            flags = []
            if c.get("is_primary_key"):
                flags.append("PK")
            if c.get("is_lookup_column"):
                flags.append("Lookup")
            flag_str = f" ({','.join(flags)})" if flags else ""
            cdesc = c.get("description")
            desc_str = f": {cdesc}" if cdesc else ""
            col_strs.append(f"{cname} [{dtype}{flag_str}]{desc_str}")

        if col_strs:
            lines.append(f"  Cột ({len(col_strs)}): {', '.join(col_strs)}")
        else:
            lines.append("  Cột: (Chưa khai báo cột)")

    if relations:
        lines.append("")
        lines.append("CÁC MỐI QUAN HỆ BẢNG LIÊN KẾT (RELATIONSHIPS / JOINS):")
        for r in relations:
            src_t = r.get("source_table")
            src_c = r.get("source_column") or "ID"
            tgt_t = r.get("target_table")
            tgt_c = r.get("target_column") or "ID"
            rtype = r.get("relation_type") or "many-to-one"
            rdesc = r.get("description") or r.get("relation_label") or ""
            lines.append(f"- {src_t}.{src_c} = {tgt_t}.{tgt_c} [{rtype}] ({rdesc})")

    if lookups:
        lines.append("")
        lines.append("CÁC DANH MỤC TRA CỨU (LOOKUPS):")
        for l in lookups:
            lines.append(f"- {l.get('name')}: Nguồn {l.get('source_table')}.{l.get('id_column')} -> {l.get('name_column')}")

    return "\n".join(lines)


def get_system_prompt(schema_context):
    """Tạo System Prompt chuyên biệt cho Database Oracle và logic Supabase."""
    return f"""Bạn là **Oracle Quick Query AI** - Trợ lý thông minh chuyên sâu về Cơ sở dữ liệu Oracle và hệ thống Quản lý Metadata Supabase.

PHẠM VI NHIỆM VỤ:
1. **Chuyên sâu Database & Schema**: Bạn nắm rõ cấu trúc toàn bộ các bảng, danh sách cột, kiểu dữ liệu và mối quan hệ (JOIN) trong hệ thống được cung cấp ở phần DỮ LIỆU METADATA bên dưới.
2. **Text-to-SQL (SELECT)**:
   - Khi người dùng hỏi hoặc yêu cầu lấy dữ liệu bằng tiếng Việt, hãy viết câu lệnh SQL Oracle chính xác 100%.
   - Luôn sử dụng đúng tên bảng và tên cột có trong schema. Dùng alias ngắn gọn (t1, t2...).
   - Với các quan hệ nối bảng, sử dụng đúng các cặp cột khóa ngoại đã được khai báo.
   - Luôn dùng cú pháp Oracle chuẩn: `FETCH FIRST n ROWS ONLY` (thay vì LIMIT), `SYSDATE` (thay vì NOW()), `TRUNC()`, `NVL()`...
3. **Tạo câu lệnh INSERT & UPDATE dữ liệu**:
   - Khi được yêu cầu tạo câu lệnh INSERT hoặc UPDATE dữ liệu cho bảng, hãy liệt kê đầy đủ các cột phù hợp, kèm giá trị mẫu hợp lý theo đúng kiểu dữ liệu.
4. **Hỗ trợ thêm BẢNG MỚI vào Supabase**:
   - Khi người dùng yêu cầu tạo hoặc thêm bảng mới (metadata), hãy sinh câu lệnh SQL INSERT chuẩn vào `tables_meta` và `columns_meta`:
     ```sql
     INSERT INTO tables_meta (table_name, alias, description, schema_name, description_vi, search_keywords) VALUES
     ('TÊN_BẢNG', 'Alias', 'Mô tả', 'SCHEMA', 'Mô tả tiếng Việt', 'từ khóa');

     INSERT INTO columns_meta (table_id, column_name, data_type, is_primary_key, is_lookup_column, description) VALUES
     (1, 'CỘT_1', 'VARCHAR2', TRUE, FALSE, 'Khóa chính'),
     (1, 'CỘT_2', 'NUMBER', FALSE, FALSE, 'Mô tả...');
     ```
   - Nhắc người dùng: *"Bạn có thể copy đoạn SQL trên và dán trực tiếp vào tab **Bảng & Cột -> ➕ Nhập bảng mới -> ⚡ Dán câu lệnh SQL INSERT** để tạo ngay trên web!"*
5. **Giải thích & Phân tích logic**:
   - Giải thích ý nghĩa nghiệp vụ của bảng, phân nhóm (group_name), các bảng liên quan nếu người dùng thắc mắc.

QUY TẮC BẮT BUỘC:
- **CHỈ trả lời các câu hỏi xoay quanh Cơ sở dữ liệu, Schema, SQL và Logic Supabase**. Nếu người dùng hỏi các chủ đề ngoài lề (như viết thơ, thời tiết, lập trình game...), hãy lịch sự từ chối và nhắc nhở họ rằng bạn là trợ lý chuyên trách về Database.
- Trả lời bằng **tiếng Việt**, ngắn gọn, rõ ràng, luôn đặt mã SQL vào khối code ```sql ... ```.

{schema_context}
"""


def stream_ai_chat(messages, config, schema_context):
    """Gửi yêu cầu hội thoại đến AI và stream kết quả về."""
    api_key = config.get("api_key")
    if not api_key:
        yield "⚠️ Chưa cấu hình `AI_API_KEY` trong file `secrets.toml`. Vui lòng kiểm tra lại cấu hình."
        return

    base_url = config.get("base_url") or None
    model = config.get("model") or "deepseek-chat"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        system_msg = {"role": "system", "content": get_system_prompt(schema_context)}
        full_messages = [system_msg] + [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
            stream=True,
            temperature=0.2,
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as exc:
        yield f"❌ Lỗi kết nối AI ({config.get('provider')}): {exc}"
