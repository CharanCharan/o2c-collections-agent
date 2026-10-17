-- LangGraph durable checkpoints and bounded case workflow. Apply after 008.
begin;
alter table public.ca_collection_cases add column if not exists workflow jsonb;
create table if not exists public.ca_scenarios (
 invoice_id text primary key references public.ca_invoices(id) on delete cascade,
 data jsonb not null
);
create table if not exists public.ca_graph_checkpoints (
 case_id uuid not null references public.ca_collection_cases(id) on delete cascade,
 namespace text not null,checkpoint_id text not null,parent_id text,data jsonb not null,
 primary key(case_id,namespace,checkpoint_id)
);
create table if not exists public.ca_graph_writes (
 case_id uuid not null,namespace text not null,checkpoint_id text not null,task_id text not null,idx integer not null,data jsonb not null,
 primary key(case_id,namespace,checkpoint_id,task_id,idx),
 foreign key(case_id,namespace,checkpoint_id) references public.ca_graph_checkpoints on delete cascade
);
create table if not exists public.ca_case_effects (
 case_id uuid not null references public.ca_collection_cases(id) on delete cascade,
 event_key text not null,tool text not null,result jsonb not null,primary key(case_id,event_key,tool)
);
create table if not exists public.ca_agent_jobs (
 run_id uuid primary key references public.ca_runs(id) on delete cascade,
 session_key text not null,mode text not null check(mode in ('limited','autopilot')),
 status text not null default 'running',progress jsonb not null default '{}',updated_at timestamptz not null default now()
);
create index if not exists ca_agent_jobs_session_idx on public.ca_agent_jobs(session_key);
alter table public.ca_scenarios enable row level security;
alter table public.ca_graph_checkpoints enable row level security;
alter table public.ca_graph_writes enable row level security;
alter table public.ca_case_effects enable row level security;
alter table public.ca_agent_jobs enable row level security;
revoke all on public.ca_scenarios,public.ca_graph_checkpoints,public.ca_graph_writes,public.ca_case_effects,public.ca_agent_jobs from public,anon,authenticated;
create or replace function public.ca_workflow_health() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$ select '{"workflow_schema":9}'::jsonb; $$;
create or replace function public.ca_scenario(p_invoice_id text) returns jsonb language sql stable security definer set search_path=public,pg_temp as $$ select coalesce((select data from public.ca_scenarios where invoice_id=p_invoice_id),'{}'::jsonb); $$;
create or replace function public.ca_checkpoint(p_action text,p_case_id uuid,p_namespace text,p_checkpoint_id text default null,p_data jsonb default null)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare r public.ca_graph_checkpoints%rowtype; w jsonb;
begin
 if p_action='get' then
  select * into r from public.ca_graph_checkpoints where case_id=p_case_id and namespace=p_namespace
   and (p_checkpoint_id is null or checkpoint_id=p_checkpoint_id) order by checkpoint_id desc limit 1;
  if not found then return null; end if;
  return to_jsonb(r)||jsonb_build_object('writes',coalesce((select jsonb_agg(data order by task_id,idx) from public.ca_graph_writes
    where case_id=r.case_id and namespace=r.namespace and checkpoint_id=r.checkpoint_id),'[]'::jsonb));
 elsif p_action='put' then
  insert into public.ca_graph_checkpoints values(p_case_id,p_namespace,p_checkpoint_id,p_data->>'parent_id',p_data)
   on conflict(case_id,namespace,checkpoint_id) do update set data=excluded.data;
  -- A bounded resume window, not unlimited checkpoint time travel. Audit is separate.
  delete from public.ca_graph_checkpoints where case_id=p_case_id and namespace=p_namespace and checkpoint_id not in
   (select checkpoint_id from public.ca_graph_checkpoints where case_id=p_case_id and namespace=p_namespace order by checkpoint_id desc limit 8);
 elsif p_action='writes' then
  for w in select value from jsonb_array_elements(p_data) loop
   insert into public.ca_graph_writes values(p_case_id,p_namespace,p_checkpoint_id,w->>'task_id',(w->>'idx')::integer,w)
    on conflict(case_id,namespace,checkpoint_id,task_id,idx) do update set data=excluded.data where excluded.idx<0;
  end loop;
 else raise sqlstate 'PT409'; end if;
 return '{}'::jsonb;
end; $$;
create or replace function public.ca_workflow_patch(p_session_key text,p_case_id uuid,p_patch jsonb,p_event_key text,p_node text,p_status text,p_message text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; events jsonb; entry jsonb;
begin
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 events:=coalesce(c.workflow->'activity','[]'::jsonb);
 if not exists(select 1 from jsonb_array_elements(events) v where v->>'key'=p_event_key) then
  entry:=jsonb_build_object('key',p_event_key,'node',p_node,'status',p_status,'message',p_message,'timestamp',clock_timestamp());
  events:=events||jsonb_build_array(entry);
  select coalesce(jsonb_agg(value order by n),'[]'::jsonb) into events from jsonb_array_elements(events) with ordinality t(value,n) where n>jsonb_array_length(events)-40;
 end if;
 update public.ca_collection_cases set workflow=coalesce(workflow,'{}'::jsonb)||p_patch||jsonb_build_object('activity',events),
  collection_status=coalesce(p_patch->>'collection_status',collection_status),updated_at=clock_timestamp() where id=c.id;
 return public.ca_case_get(p_session_key,p_case_id);
end; $$;
create or replace function public.ca_workflow_effect(p_session_key text,p_case_id uuid,p_event_key text,p_tool text,p_result jsonb,p_patch jsonb)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
begin
 perform 1 from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 if exists(select 1 from public.ca_case_effects where case_id=p_case_id and event_key=p_event_key and tool=p_tool) then
  return public.ca_case_get(p_session_key,p_case_id);
 end if;
 insert into public.ca_case_effects values(p_case_id,p_event_key,p_tool,p_result);
 return public.ca_workflow_patch(p_session_key,p_case_id,p_patch,p_event_key||':'||p_tool,'execute','completed',p_result->>'message');
end; $$;
create or replace function public.ca_reply_claim(p_session_key text,p_case_id uuid,p_request_id uuid)
returns boolean language plpgsql security definer set search_path=public,pg_temp as $$
begin
 if not exists(select 1 from public.ca_collection_cases where id=p_case_id and session_key=p_session_key) then raise sqlstate 'PT404'; end if;
 update public.ca_case_messages set review='{"status":"model_attempt_reserved","review_required":true}'::jsonb
  where id=p_request_id and case_id=p_case_id and review->>'status'='pending_review';
 return found;
end; $$;
create or replace function public.ca_agent_job(p_action text,p_session_key text,p_run_id uuid,p_mode text default null,p_progress jsonb default null,p_status text default null)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare j public.ca_agent_jobs%rowtype;
begin
 perform pg_advisory_xact_lock(9009);
 if p_action='create' then
  select * into j from public.ca_agent_jobs where run_id=p_run_id for update;
  if found then
   if j.session_key<>p_session_key then raise sqlstate 'PT404'; end if;
   if j.mode<>p_mode then raise sqlstate 'PT409'; end if;
   if j.status in ('interrupted','waiting_for_portfolio') then
    if not exists(select 1 from public.ca_runs where id=p_run_id and status='completed') then raise sqlstate 'PT409'; end if;
    update public.ca_agent_jobs set status='running',updated_at=clock_timestamp() where run_id=p_run_id returning * into j;
    return jsonb_build_object('created',true,'job',to_jsonb(j)-'session_key');
   end if;
   return jsonb_build_object('created',false,'job',to_jsonb(j)-'session_key');
  end if;
  if not exists(select 1 from public.ca_runs where id=p_run_id and status='completed') then raise sqlstate 'PT409'; end if;
  insert into public.ca_agent_jobs(run_id,session_key,mode) values(p_run_id,p_session_key,p_mode) returning * into j;
  return jsonb_build_object('created',true,'job',to_jsonb(j)-'session_key');
 elsif p_action='update' then
  update public.ca_agent_jobs set progress=p_progress,status=p_status,updated_at=clock_timestamp()
   where run_id=p_run_id and session_key=p_session_key returning * into j;
 else select * into j from public.ca_agent_jobs where run_id=p_run_id and session_key=p_session_key;
 end if;
 if not found then raise sqlstate 'PT404'; end if;
 return to_jsonb(j)-'session_key';
end; $$;
create or replace function public.ca_graph_recover() returns jsonb language sql security definer set search_path=public,pg_temp as $$
 with changed as (update public.ca_agent_jobs j set status=case when r.status='completed' then 'interrupted' else 'analysis_failed' end,updated_at=clock_timestamp()
  from public.ca_runs r where r.id=j.run_id and j.status in ('running','waiting_for_portfolio') returning j.run_id)
 select jsonb_build_object('interrupted',count(*)) from changed;
$$;

-- One case per seeded invoice, plus bounded room for later examples.
create or replace function public.ca_case_open(p_session_key text,p_run_id uuid,p_invoice_id text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare cid uuid; row_data jsonb; result_data jsonb; run_status text; initial_status text;
begin
 perform pg_advisory_xact_lock(7007);
 if p_session_key is null or length(p_session_key)<>64 then raise sqlstate 'PT409'; end if;
 select id into cid from public.ca_collection_cases where session_key=p_session_key and invoice_id=p_invoice_id;
 if found then return jsonb_build_object('recorded',false,'case',public.ca_case_get(p_session_key,cid)); end if;
 select result,status into result_data,run_status from public.ca_runs where id=p_run_id;
 if run_status is null then raise sqlstate 'PT404'; end if;
 if run_status<>'completed' then raise sqlstate 'PT409'; end if;
 select value into row_data from jsonb_array_elements(result_data->'invoices') where value->>'id'=p_invoice_id;
 if row_data is null then raise sqlstate 'PT404'; end if;
 if (select count(*) from public.ca_collection_cases where session_key=p_session_key)>=32
 or (select count(*) from public.ca_collection_cases)>=500 then raise sqlstate 'PT429'; end if;
 initial_status:=case when coalesce((row_data->>'dispute')::boolean,false) then 'dispute_hold_review_required' else 'awaiting_outreach' end;
 insert into public.ca_collection_cases(session_key,run_id,invoice_id,snapshot,collection_status)
 values(p_session_key,p_run_id,p_invoice_id,jsonb_build_object('invoice',row_data,'as_of_date',result_data->'as_of_date','currency',result_data->'currency'),initial_status)
 returning id into cid;
 if row_data->'draft' is not null and row_data->'draft'<>'null'::jsonb then
  insert into public.ca_case_messages(id,case_id,channel,text)
  values(gen_random_uuid(),cid,'draft_preview',left(row_data->'draft'->>'body',4000));
 end if;
 return jsonb_build_object('recorded',true,'case',public.ca_case_get(p_session_key,cid));
end; $$;
create or replace function public.ca_case_review(p_session_key text,p_case_id uuid,p_request_id uuid,p_review jsonb)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare next_status text; old_review jsonb;
begin
 perform 1 from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select review into old_review from public.ca_case_messages where id=p_request_id and case_id=p_case_id and channel='simulated_customer_reply' for update;
 if not found then raise sqlstate 'PT404'; end if;
 if old_review->>'status' not in ('pending_review','model_attempt_reserved') then
  return jsonb_build_object('recorded',false,'case',public.ca_case_get(p_session_key,p_case_id));
 end if;
 next_status:=case when p_review->>'status'='classified_for_review' then
  case p_review->'classification'->>'intent'
   when 'dispute' then 'dispute_hold_review_required'
   when 'payment_claim' then 'reconciliation_required'
   when 'promise_to_pay' then 'promise_review_required'
   when 'request_info' then 'document_review_required'
   else 'manual_review_required' end
  else 'manual_review_required' end;
 update public.ca_case_messages set review=p_review where id=p_request_id;
 update public.ca_collection_cases set updated_at=clock_timestamp(),collection_status=
 case when collection_status='dispute_hold_review_required' then collection_status else next_status end where id=p_case_id;
 return jsonb_build_object('recorded',true,'case',public.ca_case_get(p_session_key,p_case_id));
end; $$;

do $$ declare f record; begin
 for f in select oid::regprocedure as sig from pg_proc where pronamespace='public'::regnamespace and proname in
 ('ca_workflow_health','ca_scenario','ca_checkpoint','ca_workflow_patch','ca_workflow_effect','ca_reply_claim','ca_agent_job','ca_graph_recover') loop
 execute format('revoke all on function %s from public,anon,authenticated',f.sig);
 execute format('grant execute on function %s to service_role',f.sig);
 end loop;
end $$;
create or replace function public.ca_scenarios_list() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select coalesce(jsonb_agg(jsonb_build_object('invoice_id',invoice_id,'label',data->'label','suggested_reply',data->'suggested_reply','synthetic',true) order by invoice_id),'[]'::jsonb) from public.ca_scenarios;
$$;
revoke all on function public.ca_scenarios_list() from public,anon,authenticated;
grant execute on function public.ca_scenarios_list() to service_role;
create or replace function public.ca_agent_latest(p_session_key text) returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select to_jsonb(j)-'session_key' from public.ca_agent_jobs j where session_key=p_session_key order by updated_at desc limit 1;
$$;
revoke all on function public.ca_agent_latest(text) from public,anon,authenticated;
grant execute on function public.ca_agent_latest(text) to service_role;
create or replace function public.ca_agent_plan(p_session_key text,p_run_id uuid,p_mode text) returns jsonb
language plpgsql security definer set search_path=public,pg_temp as $$
begin
 insert into public.ca_agent_jobs(run_id,session_key,mode,status) values(p_run_id,p_session_key,p_mode,'waiting_for_portfolio');
 return '{}'::jsonb;
end; $$;
revoke all on function public.ca_agent_plan(text,uuid,text) from public,anon,authenticated;
grant execute on function public.ca_agent_plan(text,uuid,text) to service_role;
notify pgrst,'reload schema';
commit;
