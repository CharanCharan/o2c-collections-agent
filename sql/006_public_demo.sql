-- M6: session ownership and durable public-demo quotas. Additive, service only.
begin;
create table if not exists public.ca_run_access (
 run_id uuid primary key references public.ca_runs(id) on delete cascade,
 session_key text not null, created_at timestamptz not null default now()
);
create index if not exists ca_run_access_session_idx on public.ca_run_access(session_key,created_at desc);
create table if not exists public.ca_demo_usage (
 day date not null, actor text not null, kind text not null check(kind in ('run','llm')),
 attempts integer not null default 0 check(attempts>=0), primary key(day,actor,kind)
);
alter table public.ca_run_access enable row level security;
alter table public.ca_demo_usage enable row level security;
revoke all on public.ca_run_access,public.ca_demo_usage from public,anon,authenticated;
create or replace function public.ca_public_health() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select '{"public_schema_version":6}'::jsonb;
$$;
create or replace function public.ca_public_reserve(p_actor text,p_kind text,p_owner boolean default false)
returns boolean language plpgsql security definer set search_path=public,pg_temp as $$
declare d date:=(now() at time zone 'UTC')::date; global_cap integer; actor_cap integer;
begin
 if p_kind not in ('run','llm') or p_actor is null or length(p_actor)>80 or p_actor='global' then raise sqlstate 'PT409'; end if;
 perform pg_advisory_xact_lock(6006);
 global_cap:=case when p_kind='run' then 20 else 40 end;
 actor_cap:=case when p_owner or p_actor='webhook' then global_cap when p_kind='run' then 3 else 8 end;
 if coalesce((select attempts from public.ca_demo_usage where day=d and actor='global' and kind=p_kind),0)>=global_cap
 or coalesce((select attempts from public.ca_demo_usage where day=d and actor=p_actor and kind=p_kind),0)>=actor_cap then return false; end if;
 insert into public.ca_demo_usage(day,actor,kind,attempts) values(d,'global',p_kind,1),(d,p_actor,p_kind,1)
 on conflict(day,actor,kind) do update set attempts=ca_demo_usage.attempts+1;
 return true;
end; $$;
create or replace function public.ca_public_create(p_run_id uuid,p_process_id uuid,p_initial_result jsonb,p_session_key text,p_owner boolean default false)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare result jsonb;
begin
 if not public.ca_public_reserve(p_session_key,'run',p_owner) then raise sqlstate 'PT429' using message='Demo daily run limit'; end if;
 result:=public.ca_create_run(p_run_id,p_process_id,p_initial_result);
 insert into public.ca_run_access(run_id,session_key) values(p_run_id,p_session_key);
 return result;
end; $$;
create or replace function public.ca_public_allowed(p_run_id uuid,p_session_key text) returns boolean
language sql stable security definer set search_path=public,pg_temp as $$
 select exists(select 1 from public.ca_run_access where run_id=p_run_id and session_key=p_session_key);
$$;
create or replace function public.ca_public_recent(p_session_key text) returns jsonb
language sql stable security definer set search_path=public,pg_temp as $$
 select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at desc),'[]'::jsonb) from
 (select r.id as run_id,r.status,r.created_at from public.ca_runs r join public.ca_run_access a on a.run_id=r.id
 where a.session_key=p_session_key order by r.created_at desc limit 20)t;
$$;
revoke all on function public.ca_public_health(),public.ca_public_reserve(text,text,boolean),public.ca_public_create(uuid,uuid,jsonb,text,boolean),public.ca_public_allowed(uuid,text),public.ca_public_recent(text) from public,anon,authenticated;
grant execute on function public.ca_public_health(),public.ca_public_reserve(text,text,boolean),public.ca_public_create(uuid,uuid,jsonb,text,boolean),public.ca_public_allowed(uuid,text),public.ca_public_recent(text) to service_role;
notify pgrst,'reload schema';
commit;
