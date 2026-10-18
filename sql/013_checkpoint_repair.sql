-- Repair bounded LangGraph checkpoint persistence. Apply AFTER 012.
-- Replaces functions only; preserves source invoices, cases, runs and mail receipts.
begin;
create or replace function public.ca_checkpoint(p_action text,p_case_id uuid,p_namespace text,p_checkpoint_id text default null,p_data jsonb default null)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
-- checkpoint-storage-v13
 declare saved public.ca_graph_checkpoints%rowtype; item jsonb; oldest text; retained integer;
begin
 if p_action='get' then
  select cp.* into saved from public.ca_graph_checkpoints as cp
   where cp.case_id=p_case_id and cp.namespace=p_namespace
    and (p_checkpoint_id is null or cp.checkpoint_id=p_checkpoint_id)
   order by cp.checkpoint_id desc limit 1;
  if not found then return null; end if;
  return to_jsonb(saved)||jsonb_build_object('writes',coalesce((
   select jsonb_agg(cw.data order by cw.task_id,cw.idx)
   from public.ca_graph_writes as cw where cw.case_id=saved.case_id
    and cw.namespace=saved.namespace and cw.checkpoint_id=saved.checkpoint_id),'[]'::jsonb));
 end if;
 if p_action not in ('put','writes') then raise sqlstate 'PT409'; end if;
 -- Serialize retention and writes for this case/namespace. No global job lock.
 perform pg_advisory_xact_lock(hashtextextended(p_case_id::text||':'||p_namespace,9013));
 if p_action='put' then
  insert into public.ca_graph_checkpoints as cp(case_id,namespace,checkpoint_id,parent_id,data)
   values(p_case_id,p_namespace,p_checkpoint_id,p_data->>'parent_id',p_data)
   on conflict(case_id,namespace,checkpoint_id) do update set data=excluded.data;
  delete from public.ca_graph_checkpoints as cp where cp.case_id=p_case_id and cp.namespace=p_namespace
   and cp.checkpoint_id not in (select keep.checkpoint_id from public.ca_graph_checkpoints as keep
    where keep.case_id=p_case_id and keep.namespace=p_namespace order by keep.checkpoint_id desc limit 8);
 else
  if not exists(select 1 from public.ca_graph_checkpoints as cp where cp.case_id=p_case_id
    and cp.namespace=p_namespace and cp.checkpoint_id=p_checkpoint_id) then
   select min(cp.checkpoint_id),count(*) into oldest,retained from public.ca_graph_checkpoints as cp
    where cp.case_id=p_case_id and cp.namespace=p_namespace;
   -- A delayed write for a checkpoint outside the retained resume window is
   -- obsolete. Never recreate it or erase newer state to satisfy the old write.
   if retained>=8 and p_checkpoint_id<oldest then return '{"retired":true}'::jsonb; end if;
   -- Unknown/newer checkpoint references remain errors; do not mask corruption.
   raise foreign_key_violation using message='Checkpoint write references an unavailable checkpoint';
  end if;
  for item in select value from jsonb_array_elements(p_data) loop
   insert into public.ca_graph_writes as cw(case_id,namespace,checkpoint_id,task_id,idx,data)
    values(p_case_id,p_namespace,p_checkpoint_id,item->>'task_id',(item->>'idx')::integer,item)
    on conflict(case_id,namespace,checkpoint_id,task_id,idx) do update set data=excluded.data where excluded.idx<0;
  end loop;
 end if;
 return '{}'::jsonb;
end; $$;
create or replace function public.ca_checkpoint_health() returns jsonb
language sql stable security definer set search_path=public,pg_temp as $$
 select jsonb_build_object('checkpoint_schema',13,'retention',8,'ready',
  position('checkpoint-storage-v13' in pg_get_functiondef('public.ca_checkpoint(text,uuid,text,text,jsonb)'::regprocedure))>0);
$$;
revoke all on function public.ca_checkpoint(text,uuid,text,text,jsonb) from public,anon,authenticated;
grant execute on function public.ca_checkpoint(text,uuid,text,text,jsonb) to service_role;
revoke all on function public.ca_checkpoint_health() from public,anon,authenticated;
grant execute on function public.ca_checkpoint_health() to service_role;
notify pgrst,'reload schema';
commit;
-- Expected: checkpoint_schema 13, retention 8, ready true.
select public.ca_checkpoint_health();
