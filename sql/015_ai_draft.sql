-- Explicit visitor-requested AI drafts. Apply after SQL014; preserve source/runs/mail.
begin;
alter table public.ca_collection_cases add column if not exists draft_generation jsonb;
create table if not exists public.ca_draft_attempts (
 id uuid primary key,
 case_id uuid not null references public.ca_collection_cases(id) on delete cascade,
 instructions_hash text not null check(length(instructions_hash)=64),
 status text not null check(status in ('reserved','completed','failed','superseded')),
 created_at timestamptz not null default clock_timestamp(),
 audit jsonb, reason text
);
create index if not exists ca_draft_attempt_case_idx on public.ca_draft_attempts(case_id,created_at);
create unique index if not exists ca_draft_attempt_active_idx on public.ca_draft_attempts(case_id) where status='reserved';
alter table public.ca_draft_attempts enable row level security;
revoke all on public.ca_draft_attempts from public,anon,authenticated;

create or replace function public.ca_ai_draft_health() returns jsonb
language sql stable security definer set search_path=public,pg_temp as $$
 select '{"ready":true,"schema":15}'::jsonb;
$$;

create or replace function public.ca_draft_editable(p_case_id uuid) returns boolean
language sql stable security definer set search_path=public,pg_temp as $$
 select coalesce(c.collection_status='awaiting_outreach'
  and coalesce((c.snapshot->'invoice'->>'eligible')::boolean,false)
  and not coalesce((c.snapshot->'invoice'->>'dispute')::boolean,false)
  and jsonb_typeof(c.snapshot->'invoice'->'draft')='object'
  and not coalesce((c.workflow->>'processing')::boolean,false)
  and coalesce(c.workflow->'followup','null'::jsonb)='null'::jsonb
  and (c.workflow is null or c.workflow->>'status' in ('awaiting_approval','ready_for_outreach','quota_wait'))
  and (c.workflow->'pending'->>'tool' is null or c.workflow->'pending'->>'tool'='send_email')
  and not exists(select 1 from public.ca_case_messages where case_id=c.id and channel='simulated_customer_reply')
  and not exists(select 1 from public.ca_case_mail where case_id=c.id)
  and not exists(select 1 from public.ca_mail_messages where run_id=c.run_id and invoice_id=c.invoice_id),false)
 from public.ca_collection_cases c where c.id=p_case_id;
$$;

create or replace function public.ca_ai_draft(p_action text,p_session_key text,p_case_id uuid,p_request_id uuid,
 p_instructions_hash text,p_draft jsonb default null,p_audit jsonb default null,p_reason text default null)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; a public.ca_draft_attempts%rowtype; events jsonb; info jsonb;
begin
 -- Same ordering as mail reservation; serialize draft commit against send intents.
 perform pg_advisory_xact_lock(5005);
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select * into a from public.ca_draft_attempts where id=p_request_id;
 if found and (a.case_id<>p_case_id or a.instructions_hash<>p_instructions_hash) then raise sqlstate 'PT409'; end if;
 if p_action='claim' then
  if a.id is not null then
   return jsonb_build_object('recorded',false,'generated',a.status='completed','status',a.status,
    'reason',coalesce(a.reason,'This request was already reserved. No repeat model call; keep the current draft.'),
    'audit',a.audit,'case',public.ca_case_get(p_session_key,p_case_id));
  end if;
  if not coalesce(public.ca_draft_editable(p_case_id),false) then raise sqlstate 'PT409' using message='Only an eligible unsent reminder without a response can be redrafted'; end if;
  if exists(select 1 from public.ca_draft_attempts where case_id=p_case_id and status='reserved' and created_at>clock_timestamp()-interval '5 minutes') then
   raise sqlstate 'PT409' using message='Draft generation is already in progress';
  end if;
  update public.ca_draft_attempts set status='superseded',reason='Earlier generation has no saved result. No automatic repeat call.'
   where case_id=p_case_id and status='reserved';
  insert into public.ca_draft_attempts(id,case_id,instructions_hash,status) values(p_request_id,p_case_id,p_instructions_hash,'reserved') returning * into a;
  update public.ca_collection_cases set draft_generation=jsonb_build_object('request_id',a.id,'status','reserved','created_at',a.created_at),updated_at=clock_timestamp() where id=p_case_id;
  return jsonb_build_object('recorded',true,'case',public.ca_case_get(p_session_key,p_case_id));
 end if;
 if p_action not in ('complete','fail') or a.id is null then raise sqlstate 'PT409'; end if;
 if a.status<>'reserved' then
  return jsonb_build_object('recorded',false,'generated',a.status='completed','status',a.status,'reason',a.reason,'audit',a.audit,'case',public.ca_case_get(p_session_key,p_case_id));
 end if;
 if p_action='complete' and coalesce(public.ca_draft_editable(p_case_id),false) then
  if jsonb_typeof(p_draft)<>'object' or p_draft->>'generation_mode'<>'llm_assisted_validated_facts'
   or length(coalesce(p_draft->>'body','')) not between 1 and 4000 or length(coalesce(p_draft->>'subject','')) not between 1 and 200 then raise sqlstate 'PT409'; end if;
  update public.ca_collection_cases set snapshot=jsonb_set(jsonb_set(snapshot,'{invoice,draft}',p_draft),'{invoice,draft_audit}',p_audit) where id=p_case_id;
  update public.ca_case_messages set text=p_draft->>'body' where case_id=p_case_id and channel='draft_preview';
  if not found then insert into public.ca_case_messages(id,case_id,channel,text) values(gen_random_uuid(),p_case_id,'draft_preview',p_draft->>'body'); end if;
  a.status:='completed'; a.reason:='AI draft saved. Review it before sending.';
 else
  a.status:='failed'; a.reason:=case when p_action='complete' then 'The case changed while drafting. Existing draft retained.' else left(coalesce(p_reason,'Generation failed. Existing draft retained.'),600) end;
 end if;
 update public.ca_draft_attempts set status=a.status,audit=p_audit,reason=a.reason where id=p_request_id;
 info:=jsonb_build_object('request_id',a.id,'status',a.status,'created_at',a.created_at,'reason',a.reason,'audit',p_audit);
 update public.ca_collection_cases set draft_generation=info,updated_at=clock_timestamp() where id=p_case_id;
 if c.workflow is not null then
  events:=coalesce(c.workflow->'activity','[]'::jsonb)||jsonb_build_array(jsonb_build_object('key',p_request_id::text||':redraft','node','redraft',
   'status',case when a.status='completed' then 'completed' else 'warning' end,'message',a.reason,'timestamp',clock_timestamp()));
  select coalesce(jsonb_agg(value order by n),'[]'::jsonb) into events from jsonb_array_elements(events) with ordinality e(value,n) where n>jsonb_array_length(events)-40;
  update public.ca_collection_cases set workflow=jsonb_set(workflow,'{activity}',events) where id=p_case_id;
 end if;
 return jsonb_build_object('recorded',true,'generated',a.status='completed','status',a.status,'reason',a.reason,'audit',p_audit,'case',public.ca_case_get(p_session_key,p_case_id));
end; $$;

-- Preserve existing send semantics; bind the payload to the current saved draft.
create or replace function public.ca_case_mail_prepare(p_session_key text,p_case_id uuid,p_id uuid,p_payload jsonb,p_reply_to text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; job jsonb;
begin
 perform pg_advisory_xact_lock(5005);
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select to_jsonb(m) into job from public.ca_case_mail l join public.ca_mail_messages m on m.id=l.mail_id where l.case_id=c.id;
 if job->>'state'='accepted' then return job; end if;
 if c.collection_status<>'awaiting_outreach' then raise sqlstate 'PT409' using message='Case needs review before further reminders'; end if;
 if exists(select 1 from public.ca_draft_attempts where case_id=c.id and status='reserved' and created_at>clock_timestamp()-interval '5 minutes') then
  raise sqlstate 'PT409' using message='Wait for draft generation before sending'; end if;
 if p_payload->>'subject' is distinct from '[O2C DEMO] '||(c.snapshot->'invoice'->'draft'->>'subject')
 or p_payload->>'text' is distinct from E'SYNTHETIC COLLECTIONS DEMO — no real debt or payment request.\n\n'||(c.snapshot->'invoice'->'draft'->>'body') then
  raise sqlstate 'PT409' using message='Draft changed; refresh and review before sending'; end if;
 job:=public.ca_mail_prepare(c.run_id,c.invoice_id,p_id,p_payload,p_reply_to);
 insert into public.ca_case_mail(case_id,mail_id) values(c.id,(job->>'id')::uuid) on conflict(case_id) do nothing;
 if job->>'state'='accepted' then update public.ca_collection_cases set collection_status='awaiting_response' where id=c.id and collection_status='awaiting_outreach'; end if;
 return job;
end; $$;
revoke all on function public.ca_ai_draft_health(),public.ca_draft_editable(uuid),public.ca_ai_draft(text,text,uuid,uuid,text,jsonb,jsonb,text) from public,anon,authenticated;
grant execute on function public.ca_ai_draft_health(),public.ca_draft_editable(uuid),public.ca_ai_draft(text,text,uuid,uuid,text,jsonb,jsonb,text) to service_role;
notify pgrst,'reload schema';
commit;
