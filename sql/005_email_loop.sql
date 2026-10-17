-- M5: controlled email intent, webhook receipt and follow-up tasks. Additive.
begin;
create table if not exists public.ca_mail_messages (
 id uuid primary key, run_id uuid not null references public.ca_runs(id) on delete cascade,
 invoice_id text not null, created_at timestamptz not null default now(),
 state text not null default 'reserved' check(state in ('reserved','accepted','uncertain')),
 payload jsonb not null, reply_to text not null unique, provider_id text unique,
 last_error text, unique(run_id,invoice_id)
);
create table if not exists public.ca_mail_webhooks (
 event_id text primary key, mail_id uuid not null references public.ca_mail_messages(id) on delete cascade,
 event_type text not null, received_at timestamptz not null default now(), evidence jsonb not null
);
create table if not exists public.ca_mail_replies (
 id text primary key, mail_id uuid not null references public.ca_mail_messages(id) on delete cascade,
 created_at timestamptz not null default now(), review jsonb not null,
 resolution jsonb
);
create table if not exists public.ca_followups (
 reply_id text primary key references public.ca_mail_replies(id) on delete cascade,
 due_date date not null, task text not null, state text not null default 'scheduled',
 created_at timestamptz not null default now()
);
alter table public.ca_mail_messages enable row level security;
alter table public.ca_mail_webhooks enable row level security;
alter table public.ca_mail_replies enable row level security;
alter table public.ca_followups enable row level security;
revoke all on public.ca_mail_messages,public.ca_mail_webhooks,public.ca_mail_replies,public.ca_followups from public,anon,authenticated;

create or replace function public.ca_mail_health() returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select '{"mail_schema_version":5}'::jsonb;
$$;
-- Internal helper: lock run, append actual post-run activity, preserve finance snapshot.
create or replace function public.ca_mail_event(p_run_id uuid,p_stage text,p_status text,p_message text,p_data jsonb)
returns void language plpgsql security definer set search_path=public,pg_temp as $$
declare n bigint;
begin
 select last_event_id+1 into n from public.ca_runs where id=p_run_id for update;
 insert into public.ca_run_events values(p_run_id,n,gen_random_uuid(),jsonb_build_object(
 'run_id',p_run_id,'event_id',n,'stage',p_stage,'status',p_status,'timestamp',now(),
 'message',p_message,'result',p_data));
 update public.ca_runs set last_event_id=n,updated_at=now() where id=p_run_id;
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
 select * into m from public.ca_mail_messages where run_id=p_run_id and invoice_id=p_invoice_id;
 if found then return to_jsonb(m); end if;
 if (select count(*) from public.ca_mail_messages where created_at >= date_trunc('day',now() at time zone 'UTC') at time zone 'UTC')>=10 then
 raise sqlstate 'PT429' using message='Daily mail cap'; end if;
 insert into public.ca_mail_messages(id,run_id,invoice_id,payload,reply_to)
 values(p_id,p_run_id,p_invoice_id,p_payload,p_reply_to) returning * into m;
 perform public.ca_mail_event(p_run_id,'email_approval','completed','Owner approved this reminder for the configured test inbox; send intent saved.',
 jsonb_build_object('mail_id',p_id,'invoice_id',p_invoice_id,'provider_accepted',false));
 return to_jsonb(m);
end; $$;
create or replace function public.ca_mail_finish(p_id uuid,p_provider_id text,p_error text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare m public.ca_mail_messages%rowtype;
begin
 select * into m from public.ca_mail_messages where id=p_id for update;
 if not found then raise sqlstate 'PT404'; end if;
 if m.state='accepted' then return to_jsonb(m); end if;
 update public.ca_mail_messages set state=case when p_provider_id is not null then 'accepted' else 'uncertain' end,
 provider_id=p_provider_id,last_error=p_error where id=p_id returning * into m;
 perform public.ca_mail_event(m.run_id,'email_send',case when p_provider_id is null then 'warning' else 'completed' end,
 case when p_provider_id is null then 'Email attempt needs review; acceptance is unknown. No automatic retry.' else 'Resend accepted the email. Delivery is not yet confirmed.' end,
 jsonb_build_object('mail_id',m.id,'invoice_id',m.invoice_id,'provider_id',p_provider_id,'state',m.state,'error',p_error));
 return to_jsonb(m);
end; $$;
create or replace function public.ca_mail_find(p_id uuid default null,p_provider_id text default null,p_reply_to text default null)
returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select to_jsonb(m) from public.ca_mail_messages m where (p_id is not null and m.id=p_id)
 or (p_provider_id is not null and m.provider_id=p_provider_id) or(p_reply_to is not null and m.reply_to=p_reply_to) limit 1;
$$;
create or replace function public.ca_mail_seen(p_event_id text,p_reply_id text default null)
returns boolean language sql stable security definer set search_path=public,pg_temp as $$
 select exists(select 1 from public.ca_mail_webhooks where event_id=p_event_id)
 or (p_reply_id is not null and exists(select 1 from public.ca_mail_replies where id=p_reply_id));
$$;
create or replace function public.ca_mail_webhook(p_id uuid,p_event_id text,p_type text,p_evidence jsonb,p_reply_id text default null,p_review jsonb default null)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare m public.ca_mail_messages%rowtype;
begin
 select * into m from public.ca_mail_messages where id=p_id for update;
 if not found then raise sqlstate 'PT404'; end if;
 if public.ca_mail_seen(p_event_id,p_reply_id) then return '{"recorded":false}'::jsonb; end if;
 insert into public.ca_mail_webhooks(event_id,mail_id,event_type,evidence) values(p_event_id,p_id,p_type,p_evidence);
 if p_reply_id is not null then
 insert into public.ca_mail_replies(id,mail_id,review) values(p_reply_id,p_id,p_review);
 end if;
 perform public.ca_mail_event(m.run_id,case when p_reply_id is null then 'email_delivery' else 'email_reply' end,
 case when p_type in ('email.bounced','email.complained','email.failed','email.suppressed') or p_review->>'status'='quarantined' then 'warning' else 'completed' end,
 case when p_reply_id is null then 'Verified Resend delivery event recorded: '||p_type else 'Received reply stored for human review. Invoice payment state unchanged.' end,
 jsonb_build_object('mail_id',p_id,'invoice_id',m.invoice_id,'event_type',p_type,'reply_id',p_reply_id,'evidence',p_evidence));
 return '{"recorded":true}'::jsonb;
end; $$;
create or replace function public.ca_mail_resolve(p_reply_id text,p_resolution jsonb,p_due_date date,p_task text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare r public.ca_mail_replies%rowtype; m public.ca_mail_messages%rowtype;
begin
 select * into r from public.ca_mail_replies where id=p_reply_id for update;
 if not found then raise sqlstate 'PT404'; end if;
 if r.resolution is not null then return '{"recorded":false}'::jsonb; end if;
 if p_due_date < (now() at time zone 'UTC')::date or p_due_date > (now() at time zone 'UTC')::date+366 then raise sqlstate 'PT409'; end if;
 select * into m from public.ca_mail_messages where id=r.mail_id;
 update public.ca_mail_replies set resolution=p_resolution where id=p_reply_id;
 insert into public.ca_followups(reply_id,due_date,task) values(p_reply_id,p_due_date,p_task);
 perform public.ca_mail_event(m.run_id,'followup_scheduled','completed','Human-reviewed follow-up task saved. No automatic email or payment update.',
 jsonb_build_object('invoice_id',m.invoice_id,'reply_id',p_reply_id,'due_date',p_due_date,'task',p_task,'resolution',p_resolution));
 return '{"recorded":true}'::jsonb;
end; $$;
create or replace function public.ca_mail_state(p_run_id uuid) returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select jsonb_build_object(
 'messages',coalesce((select jsonb_agg(to_jsonb(m) order by m.created_at) from public.ca_mail_messages m where run_id=p_run_id),'[]'::jsonb),
 'replies',coalesce((select jsonb_agg(to_jsonb(r) order by r.created_at) from public.ca_mail_replies r join public.ca_mail_messages m on m.id=r.mail_id where m.run_id=p_run_id),'[]'::jsonb),
 'delivery_events',coalesce((select jsonb_agg(to_jsonb(w) order by w.received_at) from public.ca_mail_webhooks w join public.ca_mail_messages m on m.id=w.mail_id where m.run_id=p_run_id),'[]'::jsonb),
 'followups',coalesce((select jsonb_agg(to_jsonb(f) order by f.due_date) from public.ca_followups f join public.ca_mail_replies r on r.id=f.reply_id join public.ca_mail_messages m on m.id=r.mail_id where m.run_id=p_run_id),'[]'::jsonb));
$$;
revoke all on function public.ca_mail_health(),public.ca_mail_event(uuid,text,text,text,jsonb),public.ca_mail_prepare(uuid,text,uuid,jsonb,text),public.ca_mail_finish(uuid,text,text),public.ca_mail_find(uuid,text,text),public.ca_mail_seen(text,text),public.ca_mail_webhook(uuid,text,text,jsonb,text,jsonb),public.ca_mail_resolve(text,jsonb,date,text),public.ca_mail_state(uuid) from public,anon,authenticated;
grant execute on function public.ca_mail_health(),public.ca_mail_prepare(uuid,text,uuid,jsonb,text),public.ca_mail_finish(uuid,text,text),public.ca_mail_find(uuid,text,text),public.ca_mail_seen(text,text),public.ca_mail_webhook(uuid,text,text,jsonb,text,jsonb),public.ca_mail_resolve(text,jsonb,date,text),public.ca_mail_state(uuid) to service_role;
notify pgrst,'reload schema';
commit;
