-- V2.5: browser demo clock, resumable due checks and separate real follow-up intents.
-- Apply after SQL011. All changes additive; source AR and real UTC dates unchanged.
begin;
create table if not exists public.ca_demo_clocks (
 session_key text primary key check(length(session_key)=64),base_date date not null,demo_date date not null
);
create table if not exists public.ca_due_jobs (
 id uuid primary key,session_key text not null,as_of_date date not null,
 case_ids jsonb not null,status text not null default 'running',progress jsonb not null default '{}',
 created_at timestamptz not null default now(),updated_at timestamptz not null default now()
);
create index if not exists ca_due_jobs_session_idx on public.ca_due_jobs(session_key,created_at);
alter table public.ca_mail_messages add column if not exists purpose_key text not null default 'initial';
alter table public.ca_mail_messages drop constraint if exists ca_mail_messages_run_id_invoice_id_key;
create unique index if not exists ca_mail_purpose_idx on public.ca_mail_messages(run_id,invoice_id,purpose_key);
create table if not exists public.ca_case_followup_mail (
 case_id uuid not null references public.ca_collection_cases(id) on delete cascade,event_key text not null,
 mail_id uuid not null unique references public.ca_mail_messages(id) on delete cascade,primary key(case_id,event_key)
);
alter table public.ca_demo_clocks enable row level security;
alter table public.ca_due_jobs enable row level security;
alter table public.ca_case_followup_mail enable row level security;
revoke all on public.ca_demo_clocks,public.ca_due_jobs,public.ca_case_followup_mail from public,anon,authenticated;
create or replace function public.ca_followup_health() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$ select '{"schema":12}'::jsonb; $$;
create or replace function public.ca_demo_clock(p_session_key text,p_date date default null) returns jsonb
language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_demo_clocks%rowtype;
begin
 perform pg_advisory_xact_lock(12012);
 if p_session_key is null or length(p_session_key)<>64 then raise sqlstate 'PT409'; end if;
 insert into public.ca_demo_clocks select p_session_key,as_of_date,as_of_date from public.ca_demo_settings where id=1 on conflict do nothing;
 select * into c from public.ca_demo_clocks where session_key=p_session_key for update;
 if not found then raise sqlstate 'PT409'; end if;
 if p_date is not null then
  if p_date<c.demo_date or p_date>c.base_date+365 then raise sqlstate 'PT409' using message='Demo clock must move forward within one year'; end if;
  if exists(select 1 from public.ca_agent_jobs where session_key=p_session_key and status in ('running','waiting_for_portfolio'))
   or exists(select 1 from public.ca_due_jobs where session_key=p_session_key and status in ('running','interrupted'))
   or exists(select 1 from public.ca_collection_cases where session_key=p_session_key and workflow->>'processing'='true') then raise sqlstate 'PT409' using message='Wait for active processing before changing demo date'; end if;
  update public.ca_demo_clocks set demo_date=p_date where session_key=p_session_key returning * into c;
  update public.ca_collection_cases set workflow=workflow||jsonb_build_object('demo_date',p_date),updated_at=clock_timestamp()
    where session_key=p_session_key and workflow is not null;
 end if;
 return to_jsonb(c)-'session_key';
end; $$;
create or replace function public.ca_due_job(p_action text,p_session_key text,p_id uuid default null,p_data jsonb default '{}') returns jsonb
language plpgsql security definer set search_path=public,pg_temp as $$
declare j public.ca_due_jobs%rowtype;
begin
 perform pg_advisory_xact_lock(12012);
 if p_action='create' then
  select * into j from public.ca_due_jobs where id=p_id;
  if found then
   if j.session_key<>p_session_key then raise sqlstate 'PT404'; end if;
   return jsonb_build_object('created',false,'job',to_jsonb(j)-'session_key');
  end if;
  if exists(select 1 from public.ca_due_jobs where session_key=p_session_key and status in ('running','interrupted'))
   or exists(select 1 from public.ca_agent_jobs where session_key=p_session_key and status in ('running','waiting_for_portfolio')) then raise sqlstate 'PT409' using message='Wait for active processing'; end if;
  if exists(select 1 from jsonb_array_elements_text(p_data->'case_ids') v where not exists(select 1 from public.ca_collection_cases where id=v::uuid and session_key=p_session_key)) then raise sqlstate 'PT404'; end if;
  if (p_data->>'as_of_date')::date<>(select demo_date from public.ca_demo_clocks where session_key=p_session_key) then raise sqlstate 'PT409'; end if;
  insert into public.ca_due_jobs(id,session_key,as_of_date,case_ids) values(p_id,p_session_key,(p_data->>'as_of_date')::date,p_data->'case_ids') returning * into j;
  return jsonb_build_object('created',true,'job',to_jsonb(j)-'session_key');
 elsif p_action='resume' then
  select * into j from public.ca_due_jobs where id=p_id and session_key=p_session_key for update;
  if not found then raise sqlstate 'PT404'; end if;
  if j.status<>'interrupted' then return jsonb_build_object('created',false,'job',to_jsonb(j)-'session_key'); end if;
  if exists(select 1 from public.ca_due_jobs where session_key=p_session_key and status='running') or exists(select 1 from public.ca_agent_jobs where session_key=p_session_key and status in ('running','waiting_for_portfolio')) then raise sqlstate 'PT409'; end if;
  update public.ca_due_jobs set status='running',updated_at=clock_timestamp() where id=j.id returning * into j;
  return jsonb_build_object('created',true,'job',to_jsonb(j)-'session_key');
 elsif p_action='update' then
  update public.ca_due_jobs set progress=p_data->'progress',status=p_data->>'status',updated_at=clock_timestamp() where id=p_id and session_key=p_session_key returning * into j;
 else
  select * into j from public.ca_due_jobs where session_key=p_session_key and (p_id is null or id=p_id) order by created_at desc limit 1;
 end if;
 if not found and p_id is not null then raise sqlstate 'PT404'; end if;
 return case when j.id is null then null else to_jsonb(j)-'session_key' end;
end; $$;
create or replace function public.ca_mail_public(p_id uuid) returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select jsonb_build_object('id',m.id,'state',m.state,'created_at',m.created_at,'provider_id',m.provider_id,
 'subject',m.payload->'subject','body',m.payload->'text','last_error',m.last_error,'destination','project_test_inbox','channel','resend',
 'events',coalesce((select jsonb_agg(jsonb_build_object('type',w.event_type,'received_at',w.received_at) order by w.received_at,w.event_id) from public.ca_mail_webhooks w where w.mail_id=m.id and w.event_type<>'email.received'),'[]'::jsonb)) from public.ca_mail_messages m where m.id=p_id;
$$;
create or replace function public.ca_case_get(p_session_key text,p_case_id uuid) returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select to_jsonb(c)-'session_key'||jsonb_build_object('messages',coalesce((select jsonb_agg(to_jsonb(m) order by m.created_at,m.id) from public.ca_case_messages m where m.case_id=c.id),'[]'::jsonb),
 'outbound',(select public.ca_mail_public(mail_id) from public.ca_case_mail where case_id=c.id),
 'followups',coalesce((select jsonb_agg(public.ca_mail_public(l.mail_id)||jsonb_build_object('event_key',l.event_key) order by m.created_at,m.id) from public.ca_case_followup_mail l join public.ca_mail_messages m on m.id=l.mail_id where l.case_id=c.id),'[]'::jsonb))
 from public.ca_collection_cases c where c.id=p_case_id and c.session_key=p_session_key;
$$;
create or replace function public.ca_followup_mail_prepare(p_session_key text,p_case_id uuid,p_event_key text,p_id uuid,p_payload jsonb,p_reply_to text) returns jsonb
language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; m public.ca_mail_messages%rowtype; latest_reply text;
begin
 perform pg_advisory_xact_lock(5005);
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select x.* into m from public.ca_case_followup_mail l join public.ca_mail_messages x on x.id=l.mail_id where l.case_id=c.id and l.event_key=p_event_key;
 if m.state='accepted' then return to_jsonb(m); end if;
 if c.workflow->'followup'->>'event_key' is distinct from p_event_key or coalesce(c.workflow->'followup'->>'status','none') not in ('draft_ready','quota_wait','unknown','review_required')
 or coalesce((c.snapshot->'invoice'->>'dispute')::boolean,false) or c.collection_status='dispute_hold_review_required'
 or coalesce((c.workflow->'reconciliation'->>'remaining_amount')::numeric,0)<=0
 or c.workflow->'reconciliation'->>'financial_state'='review_overpayment' then raise sqlstate 'PT409' using message='Follow-up no longer permitted'; end if;
 select id::text into latest_reply from public.ca_case_messages where case_id=c.id and channel='simulated_customer_reply' order by created_at desc,id desc limit 1;
 if latest_reply is not null and latest_reply is distinct from c.workflow->>'promise_event_key' then raise sqlstate 'PT409' using message='New reply supersedes follow-up'; end if;
 if exists(select 1 from public.ca_case_mail l join public.ca_mail_messages x on x.id=l.mail_id where l.case_id=c.id and (x.state<>'accepted' or exists(select 1 from public.ca_mail_webhooks w where w.mail_id=x.id and w.event_type in ('email.bounced','email.complained','email.failed','email.suppressed')))) then raise sqlstate 'PT409' using message='Original transport needs review'; end if;
 if coalesce((c.workflow->'scenario'->>'missing_contact')::boolean,false) or c.workflow->'scenario'->>'prior_transport' is not null then raise sqlstate 'PT409'; end if;

 if exists(select 1 from public.ca_mail_replies r join public.ca_mail_messages x on x.id=r.mail_id where x.invoice_id=c.invoice_id and r.resolution->>'intent'='dispute') then raise sqlstate 'PT409'; end if;
 if m.id is not null then return to_jsonb(m); end if;
 if (select count(*) from public.ca_mail_messages where created_at>=date_trunc('day',now() at time zone 'UTC') at time zone 'UTC')>=10 then raise sqlstate 'PT429'; end if;
 insert into public.ca_mail_messages(id,run_id,invoice_id,payload,reply_to,purpose_key) values(p_id,c.run_id,c.invoice_id,p_payload,p_reply_to,'followup:'||c.id::text||':'||p_event_key) returning * into m;
 insert into public.ca_case_followup_mail values(c.id,p_event_key,m.id);
 return to_jsonb(m);
end; $$;
create or replace function public.ca_mail_prepare(p_run_id uuid,p_invoice_id text,p_id uuid,p_payload jsonb,p_reply_to text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare m public.ca_mail_messages%rowtype; r public.ca_runs%rowtype; invoice jsonb;
begin
 -- Global daily reservation cap, durable across restarts and concurrent requests.
 perform pg_advisory_xact_lock(5005);
 select * into r from public.ca_runs where id=p_run_id for update;
 if not found then raise sqlstate 'PT404'; end if;
 select v into invoice from jsonb_array_elements(r.result->'invoices') v where v->>'id'=p_invoice_id;
 if r.status<>'completed' or invoice is null or not coalesce((invoice->>'eligible')::boolean,false)
 or invoice->'draft' is null or invoice->'draft'='null'::jsonb or coalesce((invoice->>'dispute')::boolean,false) then
 raise sqlstate 'PT409'; end if;
 if exists(select 1 from public.ca_mail_replies rr join public.ca_mail_messages mm on mm.id=rr.mail_id
 where mm.invoice_id=p_invoice_id and rr.resolution->>'intent'='dispute') then
 raise sqlstate 'PT409' using message='Reviewed dispute holds further email'; end if;
 select * into m from public.ca_mail_messages where run_id=p_run_id and invoice_id=p_invoice_id and purpose_key='initial';
 if found then return to_jsonb(m); end if;
 if (select count(*) from public.ca_mail_messages where created_at >= date_trunc('day',now() at time zone 'UTC') at time zone 'UTC')>=10 then
 raise sqlstate 'PT429' using message='Daily mail cap'; end if;
 insert into public.ca_mail_messages(id,run_id,invoice_id,payload,reply_to)
 values(p_id,p_run_id,p_invoice_id,p_payload,p_reply_to) returning * into m;
 perform public.ca_mail_event(p_run_id,'email_approval','completed','Reminder send authorized for the project test inbox; send intent saved.',
 jsonb_build_object('mail_id',p_id,'invoice_id',p_invoice_id,'provider_accepted',false));
 return to_jsonb(m);
end; $$;
create or replace function public.ca_workflow_patch(p_session_key text,p_case_id uuid,p_patch jsonb,p_event_key text,p_node text,p_status text,p_message text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; events jsonb; entry jsonb;
begin
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 if p_node='load' then p_patch:=p_patch||jsonb_build_object('demo_date',coalesce((select demo_date::text from public.ca_demo_clocks where session_key=p_session_key),c.snapshot->>'as_of_date')); end if;
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
create or replace function public.ca_graph_recover() returns jsonb language sql security definer set search_path=public,pg_temp as $$
 with changed as (update public.ca_agent_jobs j set status=case when r.status='completed' then 'interrupted' else 'analysis_failed' end,updated_at=clock_timestamp() from public.ca_runs r where r.id=j.run_id and j.status in ('running','waiting_for_portfolio') returning j.run_id),
 due as (update public.ca_due_jobs set status='interrupted',updated_at=clock_timestamp() where status='running' returning id)
 select jsonb_build_object('interrupted',(select count(*) from changed),'due_interrupted',(select count(*) from due));
$$;
do $$ declare f record; begin
 for f in select oid::regprocedure as sig from pg_proc where pronamespace='public'::regnamespace and proname in ('ca_followup_health','ca_demo_clock','ca_due_job','ca_mail_public','ca_followup_mail_prepare') loop
 execute format('revoke all on function %s from public,anon,authenticated',f.sig);
 execute format('grant execute on function %s to service_role',f.sig);
 end loop;
end $$;
notify pgrst,'reload schema';
commit;
