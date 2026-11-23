-- Chạy script này trong Supabase SQL Editor nếu bạn muốn bỏ đăng nhập web
-- và cho phép ứng dụng đọc/ghi metadata bảng, cột, lookup, lịch sử mà không cần tài khoản Supabase Auth.

ALTER TABLE public.tables_meta DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.columns_meta DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.lookups DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.lookup_values DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.table_relations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_settings DISABLE ROW LEVEL SECURITY;
