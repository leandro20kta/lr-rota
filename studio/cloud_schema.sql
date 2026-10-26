-- LR Rota — tabela das viagens na nuvem (Supabase/Postgres).
-- Cada viagem pertence ao resumo SHA-256 da "chave da nuvem" do utilizador; o cliente envia a chave no cabeçalho x-lr-key.
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.trips (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  owner_hash text not null check (length(owner_hash) = 64),
  name text not null default '',
  km numeric,
  data jsonb not null
);
create index if not exists trips_owner_idx on public.trips (owner_hash, created_at desc);

create or replace function public.lr_owner() returns text language sql stable as $$
  select encode(extensions.digest(coalesce(current_setting('request.headers', true)::json->>'x-lr-key', ''), 'sha256'), 'hex')
$$;

alter table public.trips enable row level security;
drop policy if exists trips_select on public.trips;
drop policy if exists trips_insert on public.trips;
drop policy if exists trips_delete on public.trips;
create policy trips_select on public.trips for select to anon using (owner_hash = public.lr_owner() and public.lr_owner() <> encode(extensions.digest('', 'sha256'), 'hex'));
create policy trips_insert on public.trips for insert to anon with check (owner_hash = public.lr_owner() and public.lr_owner() <> encode(extensions.digest('', 'sha256'), 'hex') and pg_column_size(data) < 5000000);
create policy trips_delete on public.trips for delete to anon using (owner_hash = public.lr_owner());
grant select, insert, delete on public.trips to anon;
