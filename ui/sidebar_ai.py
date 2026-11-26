"""Giao diện Trợ lý AI Database cố định ở Sidebar (cấu hình API ẩn hoàn toàn trong secrets)."""
import streamlit as st
from core.ai_service import build_schema_context, get_ai_config, stream_ai_chat


def render(client):
    """Hiển thị khung chat AI ở Sidebar."""
    # Khởi tạo trạng thái hội thoại nếu chưa có
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = [
            {
                "role": "assistant",
                "content": "Xin chào! Tôi là trợ lý AI chuyên về Database Oracle và Supabase. Bạn có thể hỏi tôi về cấu trúc bảng, gợi ý JOIN, viết câu lệnh SELECT / INSERT / UPDATE hoặc sinh SQL để tạo bảng mới!",
            }
        ]

    config = get_ai_config()
    has_key = bool(config.get("api_key"))

    # Header và nút làm mới đoạn chat
    col_title, col_reset = st.columns([5, 1])
    with col_title:
        st.markdown("#### 🤖 Trợ lý AI Database")
    with col_reset:
        if st.button("🔄", help="Làm mới đoạn hội thoại"):
            st.session_state.ai_messages = [
                {
                    "role": "assistant",
                    "content": "Đoạn chat đã được làm mới. Hãy nhập câu hỏi bạn cần trợ giúp về Database!",
                }
            ]
            st.rerun()

    # Gợi ý nhanh các câu hỏi thường dùng
    with st.expander("💡 Gợi ý câu hỏi nhanh", expanded=False):
        q1 = st.button("📊 Tóm tắt các nhóm bảng", use_container_width=True, key="q_btn_groups")
        q2 = st.button("🔗 Các bảng liên kết G_WO_BASE", use_container_width=True, key="q_btn_wo_rels")
        q3 = st.button("✍️ Viết query đơn hàng", use_container_width=True, key="q_btn_order_query")
        q4 = st.button("➕ Tạo SQL thêm bảng mới VENDOR_PARTS", use_container_width=True, key="q_btn_new_table")

    prompt_to_send = None
    if q1:
        prompt_to_send = "Liệt kê tóm tắt các nhóm bảng hiện có trong database và chức năng của từng nhóm."
    elif q2:
        prompt_to_send = "Bảng G_WO_BASE có những bảng nào liên quan và nối qua các cột nào? Viết câu lệnh JOIN mẫu."
    elif q3:
        prompt_to_send = "Viết câu lệnh SQL Oracle lấy danh sách 50 đơn hàng mới nhất kèm thông tin WO và người tạo."
    elif q4:
        prompt_to_send = "Tạo giúp tôi câu lệnh SQL INSERT vào tables_meta và columns_meta để thêm bảng mới VENDOR_PARTS gồm các cột: PART_NO (PK), VENDOR_NAME, PRICE (NUMBER), STATUS, NOTE."

    # Hiển thị lịch sử chat
    chat_container = st.container(height=430)
    with chat_container:
        for msg in st.session_state.ai_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Ô nhập tin nhắn
    user_input = st.chat_input("Hỏi AI về DB, viết SQL, tạo bảng...", key="sidebar_chat_input")
    if user_input:
        prompt_to_send = user_input

    if prompt_to_send:
        # 1. Thêm tin nhắn của user vào lịch sử
        st.session_state.ai_messages.append({"role": "user", "content": prompt_to_send})

        # 2. Hiển thị tin nhắn user ngay trong container
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt_to_send)

            # 3. Stream câu trả lời của AI
            with st.chat_message("assistant"):
                if not has_key:
                    error_msg = "⚠️ Chưa cấu hình `AI_API_KEY` trong file `secrets.toml`. Vui lòng cấu hình API Key trong secrets để bắt đầu trò chuyện."
                    st.warning(error_msg)
                    st.session_state.ai_messages.append({"role": "assistant", "content": error_msg})
                else:
                    schema_context = build_schema_context(client)
                    response_stream = stream_ai_chat(
                        st.session_state.ai_messages,
                        config,
                        schema_context,
                    )
                    full_response = st.write_stream(response_stream)
                    st.session_state.ai_messages.append({"role": "assistant", "content": full_response})

        st.rerun()
