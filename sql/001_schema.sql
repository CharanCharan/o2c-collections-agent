-- M2: run once in your Free Supabase project's SQL Editor. Safe to re-run.
-- Dedicated ca_ names avoid collisions. No existing tables/data are dropped.
begin;

create table if not exists public.ca_demo_settings (
  id integer primary key check (id = 1),
  as_of_date date not null,
  currency text not null check (currency = 'USD')
);
create table if not exists public.ca_invoices (
  id text primary key,
  customer text not null,
  segment text not null,
  amount numeric(14,2) not null check (amount >= 0),
  due date not null,
  previous_invoices integer not null check (previous_invoices >= 0),
  late_payments integer not null check (late_payments >= 0 and late_payments <= previous_invoices),
  broken_promises integer not null check (broken_promises >= 0),
  disputed boolean not null default false
);
create table if not exists public.ca_runs (
  id uuid primary key,
  process_id uuid not null,
  status text not null check (status in ('queued','running','completed','failed','cancelled','interrupted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  input_snapshot jsonb,
  result jsonb not null default '{}',
  last_event_id bigint not null default 0
);
create table if not exists public.ca_run_events (
  run_id uuid not null references public.ca_runs(id) on delete cascade,
  event_id bigint not null,
  event_key uuid not null,
  payload jsonb not null,
  primary key (run_id,event_id),
  unique (run_id,event_key)
);
create table if not exists public.ca_interactions (
  run_id uuid not null references public.ca_runs(id) on delete cascade,
  invoice_id text not null,
  action text not null check (action = 'approved_dry_run'),
  created_at timestamptz not null default now(),
  payload jsonb not null,
  primary key (run_id,invoice_id,action)
);
create index if not exists ca_runs_created_idx on public.ca_runs(created_at desc);

-- No browser/anonymous access. Only the Python backend's secret/service-role key
-- may invoke these functions. SQL Editor owner access remains available.
alter table public.ca_demo_settings enable row level security;
alter table public.ca_invoices enable row level security;
alter table public.ca_runs enable row level security;
alter table public.ca_run_events enable row level security;
alter table public.ca_interactions enable row level security;
revoke all on public.ca_demo_settings,public.ca_invoices,public.ca_runs,
  public.ca_run_events,public.ca_interactions from public,anon,authenticated;
grant all on public.ca_demo_settings,public.ca_invoices,public.ca_runs,
  public.ca_run_events,public.ca_interactions to service_role;

create or replace function public.ca_health() returns jsonb
language sql stable security definer set search_path = public,pg_temp as $$
  select jsonb_build_object('schema_version',2,
    'seeded',exists(select 1 from public.ca_demo_settings),
    'invoice_count',(select count(*) from public.ca_invoices));
$$;

-- One database statement returns settings + all source rows consistently.
-- Cast NUMERIC to text to preserve exact decimals across the JSON boundary.
create or replace function public.ca_source() returns jsonb
language sql stable security definer set search_path = public,pg_temp as $$
  select jsonb_build_object('as_of_date',s.as_of_date,'currency',s.currency,
    'invoices',coalesce((select jsonb_agg(jsonb_build_object(
      'id',i.id,'customer',i.customer,'segment',i.segment,'amount',i.amount::text,
      'due',i.due,'previous_invoices',i.previous_invoices,
      'late_payments',i.late_payments,'broken_promises',i.broken_promises,
      'disputed',i.disputed) order by i.id) from public.ca_invoices i),'[]'::jsonb))
  from public.ca_demo_settings s where s.id=1;
$$;

create or replace function public.ca_get_run(p_run_id uuid) returns jsonb
language sql stable security definer set search_path = public,pg_temp as $$
  select jsonb_build_object('run_id',r.id,'created_at',r.created_at,'status',r.status,
    'result',r.result,'input_snapshot',r.input_snapshot,'storage','supabase_postgres',
    'events',coalesce((select jsonb_agg(e.payload order by e.event_id)
      from public.ca_run_events e where e.run_id=r.id),'[]'::jsonb),
    'interactions',coalesce((select jsonb_agg(i.payload order by i.created_at,i.invoice_id)
      from public.ca_interactions i where i.run_id=r.id),'[]'::jsonb))
  from public.ca_runs r where r.id=p_run_id;
$$;

create or replace function public.ca_create_run(
  p_run_id uuid,p_process_id uuid,p_initial_result jsonb) returns jsonb
language plpgsql security definer set search_path = public,pg_temp as $$
begin
  perform pg_advisory_xact_lock(82713521);
  if (select count(*) from public.ca_runs where status in ('queued','running')) >= 5 then
    raise sqlstate 'PT429' using message='Five runs are active. Wait or restart the single backend to recover abandoned runs.';
  end if;
  insert into public.ca_runs(id,process_id,status,result)
    values(p_run_id,p_process_id,'queued',p_initial_result);
  return jsonb_build_object('run_id',p_run_id,'status','queued');
end; $$;

-- Event append + current result/status/input update commit together.
create or replace function public.ca_append_event(
  p_run_id uuid,p_process_id uuid,p_event_key uuid,p_event jsonb,
  p_run_status text default null,p_result jsonb default null,p_input jsonb default null)
returns jsonb language plpgsql security definer set search_path = public,pg_temp as $$
declare r public.ca_runs%rowtype; existing jsonb; event jsonb; n bigint;
begin
  select * into r from public.ca_runs where id=p_run_id for update;
  if not found then raise sqlstate 'PT404' using message='Run not found'; end if;
  select payload into existing from public.ca_run_events
    where run_id=p_run_id and event_key=p_event_key;
  if found then return existing; end if;
  if r.process_id <> p_process_id or r.status not in ('queued','running') then
    raise sqlstate 'PT409' using message='Run is no longer active in this backend process';
  end if;
  n := r.last_event_id+1;
  event := p_event || jsonb_build_object('run_id',p_run_id,'event_id',n,
    'timestamp',coalesce(p_event->>'timestamp',now()::text));
  insert into public.ca_run_events values(p_run_id,n,p_event_key,event);
  update public.ca_runs set last_event_id=n,updated_at=now(),
    status=coalesce(p_run_status,status),result=coalesce(p_result,result),
    input_snapshot=coalesce(p_input,input_snapshot) where id=p_run_id;
  return event;
end; $$;

create or replace function public.ca_event_feed(p_run_id uuid,p_after bigint default 0)
returns jsonb language sql stable security definer set search_path = public,pg_temp as $$
  select jsonb_build_object('status',r.status,'events',coalesce(
    (select jsonb_agg(e.payload order by e.event_id) from public.ca_run_events e
     where e.run_id=r.id and e.event_id>p_after),'[]'::jsonb))
  from public.ca_runs r where r.id=p_run_id;
$$;

create or replace function public.ca_recent_runs() returns jsonb
language sql stable security definer set search_path = public,pg_temp as $$
  select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at desc),'[]'::jsonb)
  from (select id as run_id,status,created_at from public.ca_runs
    order by created_at desc limit 20) t;
$$;

-- One backend process per demo database. At startup, abandoned prior-process
-- work is marked interrupted, never silently resumed or claimed complete.
create or replace function public.ca_recover_runs(p_process_id uuid) returns integer
language plpgsql security definer set search_path = public,pg_temp as $$
declare r record; recovered integer:=0;
begin
  for r in select id,process_id from public.ca_runs
    where status in ('queued','running') and process_id<>p_process_id for update
  loop
    perform public.ca_append_event(r.id,r.process_id,gen_random_uuid(),
      jsonb_build_object('stage','run','status','failed',
        'message','Previous backend stopped before completion. This run is interrupted; start a new run.'),
      'interrupted');
    recovered:=recovered+1;
  end loop;
  return recovered;
end; $$;

-- Eligibility, uniqueness, invoice result update and approval event are one
-- transaction under a row lock, including retries from multiple requests.
create or replace function public.ca_approve_dry_run(p_run_id uuid,p_invoice_id text)
returns jsonb language plpgsql security definer set search_path = public,pg_temp as $$
declare r public.ca_runs%rowtype; invoice jsonb; rows jsonb; item jsonb; event jsonb; n bigint;
begin
  select * into r from public.ca_runs where id=p_run_id for update;
  if not found then raise sqlstate 'PT404' using message='Run not found'; end if;
  if r.status<>'completed' then raise sqlstate 'PT409' using message='Finish a successful run first'; end if;
  select v into invoice from jsonb_array_elements(r.result->'invoices') v
    where v->>'id'=p_invoice_id;
  if not found then raise sqlstate 'PT404' using message='Invoice not found in this run'; end if;
  if not coalesce((invoice->>'eligible')::boolean,false)
      or coalesce((invoice->>'dispute')::boolean,false)
      or invoice->'draft' is null or invoice->'draft'='null'::jsonb then
    raise sqlstate 'PT409' using message='This invoice has no eligible reminder draft';
  end if;
  if exists(select 1 from public.ca_interactions
    where run_id=p_run_id and invoice_id=p_invoice_id and action='approved_dry_run') then
    return jsonb_build_object('recorded',false,'message','Already recorded; no duplicate created',
      'run',public.ca_get_run(p_run_id));
  end if;
  item:=jsonb_build_object('invoice_id',p_invoice_id,'type','approved_dry_run',
    'timestamp',now(),'draft',invoice->'draft','email_sent',false);
  insert into public.ca_interactions(run_id,invoice_id,action,payload)
    values(p_run_id,p_invoice_id,'approved_dry_run',item);
  select jsonb_agg(case when v->>'id'=p_invoice_id then
      v || '{"contacted":true,"action":"Dry run recorded"}'::jsonb else v end order by ord)
    into rows from jsonb_array_elements(r.result->'invoices') with ordinality as a(v,ord);
  n:=r.last_event_id+1;
  event:=jsonb_build_object('run_id',p_run_id,'event_id',n,'stage','approval',
    'status','completed','timestamp',now(),
    'message','Approved dry-run reminder for '||(invoice->>'customer')||' ('||p_invoice_id||'). No email was sent.',
    'result',jsonb_build_object('invoice_id',p_invoice_id,'email_sent',false));
  insert into public.ca_run_events values(p_run_id,n,gen_random_uuid(),event);
  update public.ca_runs set result=jsonb_set(result,'{invoices}',rows),
    last_event_id=n,updated_at=now() where id=p_run_id;
  return jsonb_build_object('recorded',true,'run',public.ca_get_run(p_run_id));
end; $$;

-- Functions are backend-only; anonymous/publishable keys cannot call them.
do $$ declare f record; begin
  for f in select p.oid from pg_proc p join pg_namespace n on p.pronamespace=n.oid
    where n.nspname='public' and left(p.proname,3)='ca_'
  loop
    execute format('revoke all on function %s from public,anon,authenticated',f.oid::regprocedure);
    execute format('grant execute on function %s to service_role',f.oid::regprocedure);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
