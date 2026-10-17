-- Remove daily Start quotas, retaining browser ownership and metered-service caps.
-- Apply after SQL009/010. Does not delete runs, cases or past usage records.
begin;
create or replace function public.ca_public_reserve(p_actor text,p_kind text,p_owner boolean default false)
returns boolean language plpgsql security definer set search_path=public,pg_temp as $$
declare d date:=(now() at time zone 'UTC')::date; actor_cap integer;
begin
 if p_kind not in ('run','llm') or p_actor is null or length(p_actor)>80 or p_actor='global' then raise sqlstate 'PT409'; end if;
 -- Compatibility for older callers: starting analysis has no daily quota.
 if p_kind='run' then return true; end if;
 perform pg_advisory_xact_lock(6006);
 actor_cap:=case when p_owner or p_actor='webhook' then 40 else 8 end;
 if coalesce((select attempts from public.ca_demo_usage where day=d and actor='global' and kind='llm'),0)>=40
 or coalesce((select attempts from public.ca_demo_usage where day=d and actor=p_actor and kind='llm'),0)>=actor_cap then return false; end if;
 insert into public.ca_demo_usage(day,actor,kind,attempts) values(d,'global','llm',1),(d,p_actor,'llm',1)
 on conflict(day,actor,kind) do update set attempts=ca_demo_usage.attempts+1;
 return true;
end; $$;
create or replace function public.ca_public_create(p_run_id uuid,p_process_id uuid,p_initial_result jsonb,p_session_key text,p_owner boolean default false)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare result jsonb;
begin
 result:=public.ca_create_run(p_run_id,p_process_id,p_initial_result);
 insert into public.ca_run_access(run_id,session_key) values(p_run_id,p_session_key);
 return result;
end; $$;
create or replace function public.ca_public_health() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select '{"public_schema_version":11,"daily_run_limit_enabled":false,"daily_run_cap":null,"per_browser_runs":null}'::jsonb;
$$;
revoke all on function public.ca_public_health(),public.ca_public_reserve(text,text,boolean),public.ca_public_create(uuid,uuid,jsonb,text,boolean) from public,anon,authenticated;
grant execute on function public.ca_public_health(),public.ca_public_reserve(text,text,boolean),public.ca_public_create(uuid,uuid,jsonb,text,boolean) to service_role;
notify pgrst,'reload schema';
commit;
