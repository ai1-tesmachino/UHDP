create table if not exists public.uhdp_records (
    record_type text not null,
    id text not null,
    payload jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (record_type, id)
);

create index if not exists uhdp_records_type_updated_at_idx
    on public.uhdp_records (record_type, updated_at desc);

alter table public.uhdp_records enable row level security;

create or replace function public.uhdp_records_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists uhdp_records_set_updated_at on public.uhdp_records;
create trigger uhdp_records_set_updated_at
    before update on public.uhdp_records
    for each row execute function public.uhdp_records_set_updated_at();

revoke all on function public.uhdp_records_set_updated_at()
    from public, anon, authenticated;
grant execute on function public.uhdp_records_set_updated_at()
    to service_role;

revoke all on table public.uhdp_records from anon, authenticated;
grant all on table public.uhdp_records to service_role;
