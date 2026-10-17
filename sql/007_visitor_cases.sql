-- V2.1: bounded, browser-isolated case conversations. Additive; no AR/mail writes.
begin;
create table if not exists public.ca_collection_cases (
 id uuid primary key default gen_random_uuid(),
 session_key text not null check(length(session_key)=64),
 run_id uuid not null references public.ca_runs(id) on delete cascade,
 invoice_id text not null, snapshot jsonb not null,
 collection_status text not null default 'awaiting_outreach',
 created_at timestamptz not null default now(),updated_at timestamptz not null default now(),
 unique(session_key,invoice_id)
);
create table if not exists public.ca_case_messages (
 id uuid primary key,case_id uuid not null references public.ca_collection_cases(id) on delete cascade,
 channel text not null check(channel in ('draft_preview','simulated_customer_reply')),
 text text not null check(length(text) between 1 and 4000),
 review jsonb,created_at timestamptz not null default clock_timestamp()
);
create index if not exists ca_cases_session_idx on public.ca_collection_cases(session_key,updated_at desc);
create index if not exists ca_case_messages_case_idx on public.ca_case_messages(case_id,created_at);
create index if not exists ca_case_messages_date_idx on public.ca_case_messages(created_at);
alter table public.ca_collection_cases enable row level security;
alter table public.ca_case_messages enable row level security;
revoke all on public.ca_collection_cases,public.ca_case_messages from public,anon,authenticated;

create or replace function public.ca_case_get(p_session_key text,p_case_id uuid)
returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select to_jsonb(c)-'session_key'||jsonb_build_object('messages',
  coalesce((select jsonb_agg(to_jsonb(m) order by m.created_at,m.id) from public.ca_case_messages m where m.case_id=c.id),'[]'::jsonb))
 from public.ca_collection_cases c where c.id=p_case_id and c.session_key=p_session_key;
$$;
create or replace function public.ca_cases_list(p_session_key text)
returns jsonb language sql stable security definer set search_path=public,pg_temp as $$
 select coalesce(jsonb_agg(public.ca_case_get(p_session_key,c.id) order by c.updated_at desc),'[]'::jsonb)
 from public.ca_collection_cases c where c.session_key=p_session_key;
$$;
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
 if (select count(*) from public.ca_collection_cases where session_key=p_session_key)>=12
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
create or replace function public.ca_case_reply(p_session_key text,p_case_id uuid,p_request_id uuid,p_text text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare cid uuid; old_text text; day_start timestamptz:=date_trunc('day',now() at time zone 'UTC') at time zone 'UTC';
begin
 perform pg_advisory_xact_lock(7007);
 perform 1 from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select case_id,text into cid,old_text from public.ca_case_messages where id=p_request_id;
 if found then
  if cid<>p_case_id then raise sqlstate 'PT404'; end if;
  if old_text<>p_text then raise sqlstate 'PT409'; end if;
  return jsonb_build_object('recorded',false,'case',public.ca_case_get(p_session_key,p_case_id));
 end if;
 if p_text is null or length(trim(p_text)) not between 1 and 4000 then raise sqlstate 'PT409'; end if;
 if (select count(*) from public.ca_case_messages where case_id=p_case_id and channel='simulated_customer_reply')>=12
 or (select count(*) from public.ca_case_messages m join public.ca_collection_cases c on c.id=m.case_id
     where c.session_key=p_session_key and m.channel='simulated_customer_reply' and m.created_at>=day_start)>=20
 or (select count(*) from public.ca_case_messages where channel='simulated_customer_reply' and created_at>=day_start)>=120
 then raise sqlstate 'PT429'; end if;
 insert into public.ca_case_messages(id,case_id,channel,text,review)
 values(p_request_id,p_case_id,'simulated_customer_reply',p_text,'{"status":"pending_review","review_required":true}'::jsonb);
 update public.ca_collection_cases set updated_at=clock_timestamp(),collection_status=
 case when collection_status='dispute_hold_review_required' then collection_status else 'reply_received_review_required' end where id=p_case_id;
 return jsonb_build_object('recorded',true,'case',public.ca_case_get(p_session_key,p_case_id));
end; $$;
create or replace function public.ca_case_review(p_session_key text,p_case_id uuid,p_request_id uuid,p_review jsonb)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare next_status text; old_review jsonb;
begin
 perform 1 from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select review into old_review from public.ca_case_messages where id=p_request_id and case_id=p_case_id and channel='simulated_customer_reply' for update;
 if not found then raise sqlstate 'PT404'; end if;
 if old_review->>'status'<>'pending_review' then
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
revoke all on function public.ca_case_get(text,uuid),public.ca_cases_list(text),public.ca_case_open(text,uuid,text),public.ca_case_reply(text,uuid,uuid,text),public.ca_case_review(text,uuid,uuid,jsonb) from public,anon,authenticated;
grant execute on function public.ca_case_get(text,uuid),public.ca_cases_list(text),public.ca_case_open(text,uuid,text),public.ca_case_reply(text,uuid,uuid,text),public.ca_case_review(text,uuid,uuid,jsonb) to service_role;
notify pgrst,'reload schema';
commit;
