-- Chạy toàn bộ file này một lần trong Supabase SQL Editor.
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text, role text not null default 'USER' check (role in ('ADMIN','USER')),
  created_at timestamptz default now()
);
create table if not exists public.tables_meta (
  id bigserial primary key, table_name text not null unique, alias text, description text,
  description_vi text, color text, group_name text,
  created_by uuid references auth.users, created_at timestamptz default now(), updated_at timestamptz default now()
);
create table if not exists public.columns_meta (
  id bigserial primary key, table_id bigint references public.tables_meta on delete cascade,
  column_name text not null, data_type text, is_primary_key boolean default false,
  is_lookup_column boolean default false, is_nullable boolean default true,
  has_default boolean default false, description text, note text, unique(table_id, column_name)
);
create table if not exists public.lookups (
  id bigserial primary key, name text not null unique, source_table text, id_column text,
  name_column text, created_at timestamptz default now()
);
create table if not exists public.lookup_values (
  id bigserial primary key, lookup_id bigint references public.lookups on delete cascade,
  id_value text, display_value text, unique(lookup_id, id_value)
);
create table if not exists public.query_history (
  id bigserial primary key, name text not null, state_json jsonb, sql_text text not null,
  query_type text not null default 'SELECT' check (query_type in ('SELECT','INSERT','UPDATE')), note text,
  -- FK đến public.profiles giúp PostgREST có thể truy vấn quan hệ lịch sử/user.
  created_by uuid references public.profiles(id), created_at timestamptz default now()
);
create table if not exists public.table_relations (
  id bigserial primary key,
  source_table text not null, target_table text not null,
  source_column text, target_column text, relation_label text,
  relation_type text default 'many-to-one', description text,
  created_at timestamptz default now(),
  unique(source_table, target_table, source_column, target_column)
);
-- Nâng cấp an toàn cho database đã tạo bằng bản schema trước.
alter table public.columns_meta add column if not exists is_nullable boolean default true;
alter table public.columns_meta add column if not exists has_default boolean default false;
alter table public.columns_meta add column if not exists note text;
alter table public.tables_meta add column if not exists description_vi text;
alter table public.tables_meta add column if not exists color text;
alter table public.tables_meta add column if not exists group_name text;
alter table public.query_history add column if not exists query_type text default 'SELECT';
alter table public.query_history add column if not exists note text;
notify pgrst, 'reload schema';
create table if not exists public.app_settings (
  id bigserial primary key, key text unique, value text, updated_at timestamptz default now()
);
insert into public.app_settings(key, value) values ('oracle_version', '19c') on conflict(key) do nothing;

-- Tự tạo profile khi một người dùng được tạo trong Supabase Auth.
create or replace function public.handle_new_user() returns trigger language plpgsql security definer set search_path = public as $$
begin insert into public.profiles(id,email) values(new.id,new.email) on conflict (id) do nothing; return new; end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute procedure public.handle_new_user();

-- Hàm kiểm role, dùng trong policy để không lặp SQL.
create or replace function public.is_admin() returns boolean language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.profiles where id=auth.uid() and role='ADMIN');
$$;

alter table public.profiles enable row level security;
alter table public.tables_meta enable row level security;
alter table public.columns_meta enable row level security;
alter table public.lookups enable row level security;
alter table public.lookup_values enable row level security;
alter table public.query_history enable row level security;
alter table public.table_relations enable row level security;
alter table public.app_settings enable row level security;

-- Xóa policy cũ nếu chạy lại script.
drop policy if exists profiles_read on public.profiles; drop policy if exists profiles_admin on public.profiles;
drop policy if exists tables_read on public.tables_meta; drop policy if exists tables_admin on public.tables_meta;
drop policy if exists columns_read on public.columns_meta; drop policy if exists columns_admin on public.columns_meta;
drop policy if exists lookups_read on public.lookups; drop policy if exists lookups_admin on public.lookups;
drop policy if exists values_read on public.lookup_values; drop policy if exists values_admin on public.lookup_values;
drop policy if exists history_read on public.query_history; drop policy if exists history_insert on public.query_history; drop policy if exists history_delete on public.query_history;
drop policy if exists relations_read on public.table_relations; drop policy if exists relations_admin on public.table_relations;
create policy profiles_read on public.profiles for select to authenticated using (id=auth.uid() or public.is_admin());
create policy profiles_admin on public.profiles for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy tables_read on public.tables_meta for select to authenticated using (true);
create policy tables_admin on public.tables_meta for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy columns_read on public.columns_meta for select to authenticated using (true);
create policy columns_admin on public.columns_meta for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy lookups_read on public.lookups for select to authenticated using (true);
create policy lookups_admin on public.lookups for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy values_read on public.lookup_values for select to authenticated using (true);
create policy values_admin on public.lookup_values for all to authenticated using (public.is_admin()) with check (public.is_admin());
-- Lịch sử được team cùng xem; chỉ tác giả hoặc admin mới được xóa.
create policy history_read on public.query_history for select to authenticated using (true);
create policy history_insert on public.query_history for insert to authenticated with check (created_by=auth.uid());
create policy history_delete on public.query_history for delete to authenticated using (created_by=auth.uid() or public.is_admin());
create policy relations_read on public.table_relations for select to authenticated using (true);
create policy relations_admin on public.table_relations for all to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists settings_read on public.app_settings; drop policy if exists settings_admin on public.app_settings;
create policy settings_read on public.app_settings for select to authenticated using (true);
create policy settings_admin on public.app_settings for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- Dữ liệu mẫu. Có thể xóa sau khi kiểm thử.
insert into public.tables_meta(table_name,alias,description) values
 ('DONHANG','t1','Đơn hàng'),('USERS','t2','Người dùng'),('STATUS','t3','Trạng thái') on conflict (table_name) do nothing;
insert into public.columns_meta(table_id,column_name,data_type,is_primary_key,is_lookup_column)
select t.id, v.name, v.dtype, v.pk, v.lkp from public.tables_meta t join (values
 ('DONHANG','ID','NUMBER',true,false),('DONHANG','MA_DON','VARCHAR2',false,false),('DONHANG','USER_ID','NUMBER',false,true),('DONHANG','STATUS_ID','NUMBER',false,true),('DONHANG','NGAY_TAO','DATE',false,false),('DONHANG','GHI_CHU','VARCHAR2',false,false),
 ('USERS','ID','NUMBER',true,false),('USERS','NAME','VARCHAR2',false,false),('USERS','EMAIL','VARCHAR2',false,false),
 ('STATUS','ID','NUMBER',true,false),('STATUS','NAME','VARCHAR2',false,false)
) as v(tbl,name,dtype,pk,lkp) on t.table_name=v.tbl on conflict (table_id,column_name) do nothing;
insert into public.lookups(name,source_table,id_column,name_column) values ('USER_ID','USERS','ID','NAME'),('STATUS_ID','STATUS','ID','NAME') on conflict(name) do nothing;
insert into public.lookup_values(lookup_id,id_value,display_value)
select l.id,v.id,v.label from public.lookups l join (values
 ('USER_ID','1','An'),('USER_ID','2','Bình'),('USER_ID','3','Cường'),('USER_ID','4','Dung'),
 ('STATUS_ID','1','Active'),('STATUS_ID','2','Pending'),('STATUS_ID','3','Cancelled')
) as v(lookup_name,id,label) on l.name=v.lookup_name on conflict(lookup_id,id_value) do update set display_value=excluded.display_value;
