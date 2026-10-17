-- Six synthetic invoices. Re-running restores these source values; saved runs
-- and approvals are untouched. Owner-only learning setup, not visitor editing.
begin;
insert into public.ca_demo_settings(id,as_of_date,currency) values(1,'2026-10-17','USD')
on conflict(id) do update set as_of_date=excluded.as_of_date,currency=excluded.currency;
insert into public.ca_invoices
  (id,customer,segment,amount,due,previous_invoices,late_payments,broken_promises,disputed)
values
('INV-10482','Northstar Medical Group','Healthcare · Enterprise',86400,'2026-09-18',10,6,1,false),
('INV-10431','Meridian Components','Manufacturing · Strategic',52750,'2026-09-25',10,4,1,false),
('INV-10398','BluePeak Logistics','Transportation · Mid-market',38900,'2026-10-02',10,8,0,false),
('INV-10287','Cedar & Finch Retail','Retail · Enterprise',115200,'2026-08-22',10,9,2,false),
('INV-10405','Atlas Office Systems','Business services · Mid-market',14750,'2026-10-05',10,1,0,false),
('INV-10317','Solace Energy Partners','Energy · Enterprise',64200,'2026-09-04',10,7,1,true)
on conflict(id) do update set customer=excluded.customer,segment=excluded.segment,
  amount=excluded.amount,due=excluded.due,previous_invoices=excluded.previous_invoices,
  late_payments=excluded.late_payments,broken_promises=excluded.broken_promises,
  disputed=excluded.disputed;
commit;
select public.ca_health();
