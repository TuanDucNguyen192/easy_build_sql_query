-- Chạy file này trên Supabase SQL Editor nếu database đã được tạo từ schema cũ.
alter table public.columns_meta add column if not exists is_nullable boolean default true;
alter table public.columns_meta add column if not exists has_default boolean default false;
alter table public.query_history add column if not exists query_type text default 'SELECT';
alter table public.query_history add column if not exists note text;
alter table public.tables_meta add column if not exists description_vi text;
alter table public.tables_meta add column if not exists color text;
alter table public.tables_meta add column if not exists group_name text;
alter table public.columns_meta add column if not exists note text;

create table if not exists public.table_relations (
  id bigserial primary key,
  source_table text not null, target_table text not null,
  source_column text, target_column text, relation_label text,
  relation_type text default 'many-to-one', description text,
  created_at timestamptz default now(),
  unique(source_table, target_table, source_column, target_column)
);
alter table public.table_relations enable row level security;
drop policy if exists relations_read on public.table_relations;
drop policy if exists relations_admin on public.table_relations;
create policy relations_read on public.table_relations for select to authenticated using (true);
create policy relations_admin on public.table_relations for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- Màu và nhóm hiển thị trên sơ đồ.
update public.tables_meta set group_name = 'Đơn hàng', color = '#4A90E2'
where table_name in ('G_DN_BASE', 'G_DN_DETAIL', 'G_WO_BASE', 'G_WO_BOM', 'G_WO_BOM_SAP', 'G_WO_CUSTOMER_SN', 'G_WO_SN_BATCH');
update public.tables_meta set group_name = 'SN / Sản phẩm', color = '#50C878'
where table_name in ('G_SN_MACID', 'G_SN_STATUS', 'G_SN_TRAVEL', 'SE_SN_TRAVEL_LOG', 'G_SN_KEYPARTS', 'G_SN_KEYVALUE');
update public.tables_meta set group_name = 'Danh mục', color = '#9B59B6' where table_name like 'SYS_%';
update public.tables_meta set group_name = 'Rework', color = '#E74C3C' where table_name like 'G_REWORK%';
update public.tables_meta set group_name = 'Lịch sử', color = '#F39C12' where table_name like 'G_HT_%';
update public.tables_meta set group_name = 'Kiểm tra', color = '#1ABC9C' where table_name = 'M_CHECK_TYPE';

insert into public.table_relations (source_table, target_table, source_column, target_column, relation_label, description)
values
  ('G_DN_BASE', 'G_WO_BASE', 'DN_NO', 'DN_NO', 'wo', 'Đơn hàng sinh ra WO'),
  ('G_WO_BASE', 'G_WO_BOM', 'WO', 'WO', 'bom', 'WO có định mức BOM'),
  ('G_WO_BASE', 'G_SN_TRAVEL', 'WO', 'WORK_ORDER', 'sn', 'WO có các SN'),
  ('G_SN_TRAVEL', 'G_SN_KEYPARTS', 'SERIAL_NUMBER', 'SERIAL_NUMBER', 'keyparts', 'SN có linh kiện'),
  ('G_SN_KEYPARTS', 'SYS_PART', 'ITEM_PART_ID', 'PART_ID', 'part', 'Linh kiện thuộc danh mục'),
  ('G_SN_TRAVEL', 'SYS_PROCESS', 'PROCESS_ID', 'PROCESS_ID', 'process', 'Công đoạn'),
  ('G_SN_TRAVEL', 'SYS_TERMINAL', 'TERMINAL_NAME', 'TERMINAL_NAME', 'terminal', 'Trạm'),
  ('G_SN_KEYPARTS', 'SYS_PROCESS', 'PROCESS_ID', 'PROCESS_ID', 'process', 'Công đoạn'),
  ('G_WO_BASE', 'SYS_MODEL', 'MODEL_ID', 'MODEL_ID', 'model', 'Model sản phẩm')
on conflict (source_table, target_table, source_column, target_column) do nothing;
-- Yêu cầu PostgREST nạp lại cache cột ngay sau khi nâng cấp schema.
notify pgrst, 'reload schema';

create table if not exists public.app_settings (
  id bigserial primary key,
  key text unique,
  value text,
  updated_at timestamptz default now()
);
insert into public.app_settings(key, value) values ('oracle_version', '19c') on conflict(key) do nothing;

alter table public.app_settings enable row level security;
drop policy if exists settings_read on public.app_settings;
drop policy if exists settings_admin on public.app_settings;
create policy settings_read on public.app_settings for select to authenticated using (true);
create policy settings_admin on public.app_settings for all to authenticated
  using (public.is_admin()) with check (public.is_admin());
