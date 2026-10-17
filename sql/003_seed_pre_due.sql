-- Optional M3 source examples. Run after 001 + 002 in Supabase SQL Editor.
-- Adds/restores three synthetic invoices only; no schema change or run deletion.
begin;
do $$ begin
  if not exists(select 1 from public.ca_demo_settings where id=1) then
    raise exception 'Run 001_schema.sql and 002_seed_demo.sql first';
  end if;
end $$;
insert into public.ca_invoices
  (id,customer,segment,amount,due,previous_invoices,late_payments,broken_promises,disputed)
select v.id,v.customer,v.segment,v.amount,s.as_of_date+v.days_to_due,
       v.previous_invoices,v.late_payments,v.broken_promises,false
from public.ca_demo_settings s cross join (values
  ('INV-10501','Harbor Home Supplies','Retail',28000.00,7,10,8,1),
  ('INV-10502','Willow Tech Services','Services',19500.00,7,10,1,0),
  ('INV-10503','Vista Packaging','Manufacturing',12000.00,14,10,5,1)
) as v(id,customer,segment,amount,days_to_due,previous_invoices,late_payments,broken_promises)
where s.id=1
on conflict (id) do update set customer=excluded.customer,segment=excluded.segment,
  amount=excluded.amount,due=excluded.due,previous_invoices=excluded.previous_invoices,
  late_payments=excluded.late_payments,broken_promises=excluded.broken_promises,disputed=excluded.disputed;
commit;
