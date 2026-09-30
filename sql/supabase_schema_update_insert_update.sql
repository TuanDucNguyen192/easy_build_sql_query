-- Chạy file này trên Supabase SQL Editor nếu database đã được tạo từ schema cũ.
alter table public.columns_meta add column if not exists is_nullable boolean default true;
alter table public.columns_meta add column if not exists has_default boolean default false;
alter table public.query_history add column if not exists query_type text default 'SELECT';

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
