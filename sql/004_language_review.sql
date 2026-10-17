-- M4: one additive backend-only review RPC, no existing rows/tables dropped.
begin;
create or replace function public.ca_language_health() returns jsonb
language sql stable security definer set search_path=public,pg_temp as $$
 select '{"language_schema_version":4}'::jsonb;
$$;
create or replace function public.ca_record_reply_example(
 p_run_id uuid,p_invoice_id text,p_example_id text,p_review jsonb) returns jsonb
language plpgsql security definer set search_path=public,pg_temp as $$
declare r public.ca_runs%rowtype; invoice jsonb; rows jsonb; event jsonb; n bigint;
begin
 select * into r from public.ca_runs where id=p_run_id for update;
 if not found then raise sqlstate 'PT404' using message='Run not found'; end if;
 if r.status<>'completed' then raise sqlstate 'PT409' using message='Completed run required'; end if;
 select v into invoice from jsonb_array_elements(r.result->'invoices') v where v->>'id'=p_invoice_id;
 if not found then raise sqlstate 'PT404' using message='Invoice not found'; end if;
 if coalesce(invoice->'reply_reviews','{}'::jsonb) ? p_example_id then
   return jsonb_build_object('recorded',false,'run',public.ca_get_run(p_run_id));
 end if;
 select jsonb_agg(case when v->>'id'=p_invoice_id then v || jsonb_build_object('reply_reviews',
   coalesce(v->'reply_reviews','{}'::jsonb)||jsonb_build_object(p_example_id,p_review)) else v end order by ord)
 into rows from jsonb_array_elements(r.result->'invoices') with ordinality as a(v,ord);
 n:=r.last_event_id+1;
 event:=jsonb_build_object('run_id',p_run_id,'event_id',n,'stage','reply_classification','status','completed',
   'timestamp',now(),'message','Classified a synthetic reply example for review. No email received; no payment status changed.',
   'result',jsonb_build_object('invoice_id',p_invoice_id,'example_id',p_example_id,'review',p_review));
 insert into public.ca_run_events values(p_run_id,n,gen_random_uuid(),event);
 update public.ca_runs set result=jsonb_set(result,'{invoices}',rows),last_event_id=n,updated_at=now() where id=p_run_id;
 return jsonb_build_object('recorded',true,'run',public.ca_get_run(p_run_id));
end; $$;
revoke all on function public.ca_language_health(),public.ca_record_reply_example(uuid,text,text,jsonb) from public,anon,authenticated;
grant execute on function public.ca_language_health(),public.ca_record_reply_example(uuid,text,text,jsonb) to service_role;
notify pgrst,'reload schema';
commit;
