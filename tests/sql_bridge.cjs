// Test-only in-memory PostgreSQL. No Supabase account or real key is used.
const fs = require('node:fs');
const readline = require('node:readline');
const {PGlite} = require('@electric-sql/pglite');
(async()=>{
  const db = new PGlite();
  await db.exec('create role anon; create role authenticated; create role service_role;');
  await db.exec(fs.readFileSync('sql/001_schema.sql','utf8'));
  await db.exec(fs.readFileSync('sql/004_language_review.sql','utf8'));
  await db.exec(fs.readFileSync('sql/005_email_loop.sql','utf8'));
  await db.exec(fs.readFileSync('sql/006_public_demo.sql','utf8'));
  await db.exec(fs.readFileSync('sql/007_visitor_cases.sql','utf8'));
  await db.exec(fs.readFileSync('sql/008_case_email.sql','utf8'));
  await db.exec(fs.readFileSync('sql/009_case_workflow.sql','utf8'));
  await db.exec(fs.readFileSync('sql/011_unlimited_demo_starts.sql','utf8'));
  await db.exec(fs.readFileSync('sql/012_promise_followups.sql','utf8'));
  await db.exec(fs.readFileSync('sql/013_checkpoint_repair.sql','utf8'));
  await db.exec(fs.readFileSync('sql/014_checkpoint_write_order.sql','utf8'));
  await db.exec(fs.readFileSync('sql/015_ai_draft.sql','utf8'));
  await db.exec(fs.readFileSync('sql/017_manual_draft.sql','utf8'));
  const seed=fs.readFileSync('sql/002_seed_demo.sql','utf8');
  await db.exec(seed);
  console.log(JSON.stringify({ready:true}));
  let queue=Promise.resolve();
  const lines=readline.createInterface({input:process.stdin});
  lines.on('line',(line)=>{
    queue=queue.then(async()=>{
      const q=JSON.parse(line);
      try {
        let data;
        if(q.command==='reset') {
          await db.exec('truncate public.ca_demo_clocks; truncate public.ca_due_jobs; truncate public.ca_demo_usage; truncate public.ca_runs cascade; truncate public.ca_invoices cascade; truncate public.ca_demo_settings;');
          await db.exec(seed);
          await db.exec(fs.readFileSync('sql/014_checkpoint_write_order.sql','utf8'));data=true;
        } else if(q.command==='sql') {
          data=(await db.query(q.sql,q.params||[])).rows;
        } else if(q.command==='exec') {
          await db.exec(q.sql);data=true;
        } else if(q.command==='rpc') {
          if(!/^ca_[a-z_]+$/.test(q.name))throw Error('Invalid test function name');
          const entries=Object.entries(q.params||{});
          if(entries.some(([key])=>!/^p_[a-z_]+$/.test(key)))throw Error('Invalid parameter');
          const named=entries.map(([key],i)=>`${key} => $${i+1}`).join(',');
          const values=entries.map(([,v])=>v!==null&&typeof v==='object'?JSON.stringify(v):v);
          await db.exec('begin; set local role service_role;');
          try {
            data=(await db.query(`select public.${q.name}(${named}) as data`,values)).rows[0].data;
            await db.exec('commit');
          }catch(e){await db.exec('rollback');throw e;}
        } else throw Error('Invalid test command');
        console.log(JSON.stringify({data}));
      } catch(e) {console.log(JSON.stringify({error:{code:e.code||'TEST_ERROR',message:e.message}}));}
    });
  });
  lines.on('close',()=>queue.then(()=>db.close()));
})().catch(e=>{console.error(e);process.exitCode=1});
