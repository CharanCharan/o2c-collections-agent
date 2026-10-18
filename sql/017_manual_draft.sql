-- Save human edits atomically against the exact draft the visitor opened.
-- Apply after SQL015 (SQL016 quota increase is optional).
begin;
create or replace function public.ca_draft_edit_health() returns jsonb
language sql stable security definer set search_path=public,pg_temp as $$
 select '{"ready":true,"schema":17}'::jsonb;
$$;
create or replace function public.ca_save_draft(p_session_key text,p_case_id uuid,p_request_id uuid,
 p_content_hash text,p_expected_draft jsonb,p_draft jsonb,p_audit jsonb)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare c public.ca_collection_cases%rowtype; a public.ca_draft_attempts%rowtype; events jsonb;
begin
 perform pg_advisory_xact_lock(5005);
 select * into c from public.ca_collection_cases where id=p_case_id and session_key=p_session_key for update;
 if not found then raise sqlstate 'PT404'; end if;
 select * into a from public.ca_draft_attempts where id=p_request_id;
 if found then
  if a.case_id<>p_case_id or a.instructions_hash<>p_content_hash or a.audit->>'tool' is distinct from 'edit_reminder' then raise sqlstate 'PT409'; end if;
  return jsonb_build_object('recorded',false,'case',public.ca_case_get(p_session_key,p_case_id));
 end if;
 if not coalesce(public.ca_draft_editable(p_case_id),false)
 or c.snapshot->'invoice'->'draft' is distinct from p_expected_draft
 or exists(select 1 from public.ca_draft_attempts where case_id=p_case_id and status='reserved' and created_at>clock_timestamp()-interval '5 minutes') then
  raise sqlstate 'PT409' using message='Draft changed or case is not editable';
 end if;
 if jsonb_typeof(p_draft)<>'object' or p_draft->>'generation_mode'<>'human_edited'
 or length(coalesce(p_draft->>'body','')) not between 1 and 4000
 or length(coalesce(p_draft->>'subject','')) not between 1 and 200 then raise sqlstate 'PT409'; end if;
 -- Retire stale model requests so their late results cannot overwrite human edits.
 update public.ca_draft_attempts set status='superseded',reason='Superseded by a reviewed human edit.' where case_id=p_case_id and status='reserved';
 insert into public.ca_draft_attempts(id,case_id,instructions_hash,status,audit,reason)
 values(p_request_id,p_case_id,p_content_hash,'completed',p_audit,'Human-edited draft saved. Review before sending.');
 update public.ca_collection_cases set snapshot=jsonb_set(jsonb_set(snapshot,'{invoice,draft}',p_draft),'{invoice,draft_audit}',p_audit),
  draft_generation=jsonb_build_object('request_id',p_request_id,'status','completed','reason','Human-edited draft saved. Review before sending.','audit',p_audit),
  updated_at=clock_timestamp() where id=p_case_id;
 update public.ca_case_messages set text=p_draft->>'body' where case_id=p_case_id and channel='draft_preview';
 if not found then insert into public.ca_case_messages(id,case_id,channel,text) values(gen_random_uuid(),p_case_id,'draft_preview',p_draft->>'body'); end if;
 if c.workflow is not null then
  events:=coalesce(c.workflow->'activity','[]'::jsonb)||jsonb_build_array(jsonb_build_object('key',p_request_id::text||':edit','node','edit',
    'status','completed','message','Human-edited draft saved; no model call or email sent.','timestamp',clock_timestamp()));
  select coalesce(jsonb_agg(value order by n),'[]'::jsonb) into events from jsonb_array_elements(events) with ordinality e(value,n) where n>jsonb_array_length(events)-40;
  update public.ca_collection_cases set workflow=jsonb_set(workflow,'{activity}',events) where id=p_case_id;
 end if;
 return jsonb_build_object('recorded',true,'case',public.ca_case_get(p_session_key,p_case_id));
end; $$;
revoke all on function public.ca_draft_edit_health(),public.ca_save_draft(text,uuid,uuid,text,jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.ca_draft_edit_health(),public.ca_save_draft(text,uuid,uuid,text,jsonb,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
commit;
