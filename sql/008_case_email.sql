-- Draft-level real email: bind one send intent to its browser-owned case.
begin;
create table if not exists public.ca_case_mail (
 case_id uuid primary key references public.ca_collection_cases(id) on delete cascade,
 mail_id uuid not null unique references public.ca_mail_messages(id) on delete cascade
);
alter table public.ca_case_mail enable row level security;
revoke all on public.ca_case_mail from public,anon,authenticated;
create or replace function public.ca_case_get(p_session_key text,p_case_id uuid)
returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select to_jsonb(c)-'session_key'||jsonb_build_object('messages',
  coalesce((select jsonb_agg(to_jsonb(m) order by m.created_at,m.id) from public.ca_case_messages m where m.case_id=c.id),'[]'::jsonb),
  'outbound',(select jsonb_build_object('id',m.id,'state',m.state,'created_at',m.created_at,'provider_id',m.provider_id,
    'subject',m.payload->'subject','body',m.payload->'text','last_error',m.last_error,
    'destination','project_test_inbox','channel','resend',
    'events',coalesce((select jsonb_agg(jsonb_build_object('type',w.event_type,'received_at',w.received_at) order by w.received_at,w.event_id)
      from public.ca_mail_webhooks w where w.mail_id=m.id and w.event_type<>'email.received'),'[]'::jsonb))
   from public.ca_case_mail l join public.ca_mail_messages m on m.id=l.mail_id where l.case_id=c.id))
 from public.ca_collection_cases c where c.id=p_case_id and c.session_key=p_session_key;
$$;
create or replace function public.ca_case_mail_prepare(p_session_key text,p_case_id uuid,p_id uuid,p_payload jsonb,p_reply_to text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; job jsonb;
begin
 perform pg_advisory_xact_lock(5005);
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select to_jsonb(m) into job from public.ca_case_mail l join public.ca_mail_messages m on m.id=l.mail_id where l.case_id=c.id;
 if job->>'state'='accepted' then return job; end if;
 -- New reminders/retries must wait after any reply or dispute. No blind chasing.
 if c.collection_status<>'awaiting_outreach' then raise sqlstate 'PT409' using message='Case needs review before further reminders'; end if;
 job:=public.ca_mail_prepare(c.run_id,c.invoice_id,p_id,p_payload,p_reply_to);
 insert into public.ca_case_mail(case_id,mail_id) values(c.id,(job->>'id')::uuid) on conflict(case_id) do nothing;
 if job->>'state'='accepted' then update public.ca_collection_cases set collection_status='awaiting_response' where id=c.id and collection_status='awaiting_outreach'; end if;
 return job;
end; $$;
revoke all on function public.ca_case_mail_prepare(text,uuid,uuid,jsonb,text) from public,anon,authenticated;
grant execute on function public.ca_case_mail_prepare(text,uuid,uuid,jsonb,text) to service_role;

-- Keep historical owner API compatible; use truthful actor-neutral audit text.
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
 perform public.ca_mail_event(p_run_id,'email_approval','completed','Reminder send authorized for the project test inbox; send intent saved.',
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
 if p_provider_id is not null then
  update public.ca_collection_cases c set collection_status='awaiting_response',updated_at=clock_timestamp()
   from public.ca_case_mail l where l.case_id=c.id and l.mail_id=m.id and c.collection_status='awaiting_outreach';
 end if;
 return to_jsonb(m);
end; $$;
notify pgrst,'reload schema';
commit;
