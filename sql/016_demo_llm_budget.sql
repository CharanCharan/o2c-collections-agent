-- OPTIONAL: raise app-side demo LLM allowances. Apply after SQL015 if desired.
-- Does not reset counters or change Groq's account/rate limits or billing tier.
begin;
create or replace function public.ca_llm_budget() returns jsonb
language sql stable security definer set search_path=public,pg_temp as $$
 -- Edit these two values here; reservation and health both read this function.
 select '{"daily_llm_attempt_cap":100,"per_browser_llm_attempts":40}'::jsonb;
$$;
create or replace function public.ca_public_reserve(p_actor text,p_kind text,p_owner boolean default false)
returns boolean language plpgsql security definer set search_path=public,pg_temp as $$
declare d date:=(now() at time zone 'UTC')::date; caps jsonb:=public.ca_llm_budget(); global_cap integer; actor_cap integer;
begin
 if p_kind not in ('run','llm') or p_actor is null or length(p_actor)>80 or p_actor='global' then raise sqlstate 'PT409'; end if;
 if p_kind='run' then return true; end if;
 global_cap:=(caps->>'daily_llm_attempt_cap')::integer;
 actor_cap:=case when p_owner or p_actor='webhook' then global_cap else (caps->>'per_browser_llm_attempts')::integer end;
 if global_cap<1 or actor_cap<1 or actor_cap>global_cap then raise sqlstate 'PT409'; end if;
 perform pg_advisory_xact_lock(6006);
 if coalesce((select attempts from public.ca_demo_usage where day=d and actor='global' and kind='llm'),0)>=global_cap
 or coalesce((select attempts from public.ca_demo_usage where day=d and actor=p_actor and kind='llm'),0)>=actor_cap then return false; end if;
 insert into public.ca_demo_usage(day,actor,kind,attempts) values(d,'global','llm',1),(d,p_actor,'llm',1)
 on conflict(day,actor,kind) do update set attempts=ca_demo_usage.attempts+1;
 return true;
end; $$;
create or replace function public.ca_public_health() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select '{"public_schema_version":16,"daily_run_limit_enabled":false,"daily_run_cap":null,"per_browser_runs":null}'::jsonb||public.ca_llm_budget();
$$;
revoke all on function public.ca_llm_budget(),public.ca_public_reserve(text,text,boolean),public.ca_public_health() from public,anon,authenticated;
grant execute on function public.ca_llm_budget(),public.ca_public_reserve(text,text,boolean),public.ca_public_health() to service_role;
notify pgrst,'reload schema';
commit;
