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
- Để import hàng loạt schema thực tế, dùng khối **Import toàn bộ schema**. File CSV cần `table_name,column_name,data_type`; có thể lấy [mẫu](samples/schema_import_example.csv). Các cột tùy chọn: `is_primary_key`, `is_lookup_column`, `description`. Chạy lại cùng file sẽ cập nhật cột thay vì tạo trùng.
- Admin vào **Lookup** để khai báo cột `USER_ID` / `STATUS_ID`, thêm từng giá trị quan trọng hoặc import CSV `id,display_value`. Khi người dùng chọn cột đó trong điều kiện, ô **Giá trị** sẽ gợi ý theo tên hiển thị và sinh đúng ID vào SQL.
- Mọi người vào **Query** có thể chọn `SELECT *` cho bảng chính, hoặc chọn các cột riêng lẻ và kéo-thả để đổi thứ tự chúng trong `SELECT`. SQL cập nhật tức thời và luôn dùng `FETCH FIRST n ROWS ONLY` đúng Oracle.
- Tích **Thêm điều kiện thời gian** để tự sinh điều kiện cho hôm nay, hôm qua, 7/30 ngày gần nhất, tháng này, tháng trước hoặc khoảng ngày tự chọn. Các khoảng chọn nhanh dùng mốc Oracle `SYSDATE`, nên luôn đúng vào lúc chạy query.
- Lịch sử query dùng chung; người tạo chỉ xóa được query của mình, admin xóa được toàn bộ.

## Backup

Trong tab **Bảng & Cột**, dùng nút **Tải backup bảng CSV**. Để backup đầy đủ metadata, lookup và lịch sử, dùng Supabase Dashboard → Database → Backups hoặc xuất các bảng từ Table Editor.

## Lưu ý bảo mật

Chỉ dùng **anon key** trên Streamlit. Không bao giờ đưa `service_role` key vào secrets của ứng dụng. RLS trong schema giới hạn sửa metadata/lookup cho ADMIN.

## Cấp quyền Admin

Sau khi tạo tài khoản trong Supabase Auth, chạy trong SQL Editor (thay email đúng của bạn):

```sql
update public.profiles set role = 'ADMIN' where email = 'admin@shaoyin.com';
```

Đăng xuất rồi đăng nhập lại để app nhận role mới và hiện tab **Bảng & Cột** cùng **Lookup**.
