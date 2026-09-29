# Oracle Quick Query

Web app Streamlit tạo SQL Oracle bằng thao tác chuột. Ứng dụng không kết nối và không thực thi Oracle; SQL được copy sang DBeaver hoặc PL/SQL Developer.

## Chạy local

1. Tạo project miễn phí tại [Supabase](https://supabase.com/dashboard), vào **Project Settings → API** và copy Project URL cùng `anon` key.
2. Mở SQL Editor của project, dán và chạy toàn bộ [sql/supabase_schema.sql](sql/supabase_schema.sql). Schema tạo bảng, RLS policy và dữ liệu mẫu.
3. Trong **Authentication → Users**, tạo user bằng email/password. Chạy câu này trong SQL Editor (thay email):

```sql
update public.profiles set role = 'ADMIN' where email = 'you@company.com';
```

4. Sao chép `.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml`, điền URL và anon key. Không commit `secrets.toml`.
5. Cài và chạy:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Triển khai Streamlit Community Cloud

1. Push source code lên GitHub (bỏ qua `.streamlit/secrets.toml`).
2. Vào [share.streamlit.io](https://share.streamlit.io), chọn **New app**, repository và file `app.py`.
3. Trong **Advanced settings → Secrets**, nhập:

```toml
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "<anon-key>"
```

4. Deploy. URL được tạo ra có thể gửi cho team. Mỗi đồng nghiệp cần có tài khoản trong Supabase Auth.

## Sử dụng

- Admin vào **Bảng & Cột** để thêm metadata hoặc import CSV cột có header `column_name,data_type`.
- Admin vào **Lookup** để khai báo cột `USER_ID` / `STATUS_ID` và import CSV `id,display_value`.
- Mọi người vào **Query**, chọn bảng, cột, JOIN, điều kiện, sắp xếp. SQL cập nhật tức thời và luôn dùng `FETCH FIRST n ROWS ONLY` đúng Oracle.
- Lịch sử query dùng chung; người tạo chỉ xóa được query của mình, admin xóa được toàn bộ.

## Backup

Trong tab **Bảng & Cột**, dùng nút **Tải backup bảng CSV**. Để backup đầy đủ metadata, lookup và lịch sử, dùng Supabase Dashboard → Database → Backups hoặc xuất các bảng từ Table Editor.

## Lưu ý bảo mật

Chỉ dùng **anon key** trên Streamlit. Không bao giờ đưa `service_role` key vào secrets của ứng dụng. RLS trong schema giới hạn sửa metadata/lookup cho ADMIN.
