# Entire workflow

From receivables to a recorded collection outcome.

| Step | What happens | Technology |
| --- | --- | --- |
| Load | Read synthetic invoices and saved cases. | Supabase PostgreSQL over HTTPS RPC |
| Validate | Check dates, balances and invoice history. | Python, Pydantic and Decimal |
| Assess and predict | Apply urgency rules and two trained payment-risk models. | Python; logistic models trained with scikit-learn, exported as JSON |
| Prioritize and draft | Rank eligible invoices and prepare reminders. | Python rules; optional Groq LLM phrasing with validated facts and template fallback |
| Customize a reminder | Open an unsent reminder → Draft with AI → optional wording preferences → Generate draft. Review before Send reminder. | One explicit LLM call with Python validation; saved case draft in Supabase |
| Process invoices | Choose an action, pause for approval or execute within policy. | LangGraph with Supabase checkpoints |
| Send and respond | Send real email to the demo inbox [Inbox screenshot](/assets/demo-email-inbox.png); process website-simulated replies. | Resend API, signed delivery webhooks and optional LLM reply interpretation |
| Show results | Display invoice status, completed actions and run statistics. | FastAPI, HTML/CSS/JavaScript and live SSE events |

Hosting: one Python service on Render, backed by Supabase. Opening this guide makes no LLM call.

---

# Agentic workflow

One saved LangGraph case per invoice in this browser session.

| Agent step | Decision or action | Backend |
| --- | --- | --- |
| Load | Restore invoice, conversation and current case state. | Supabase and LangGraph checkpointer |
| Interpret | Extract reply intent, promise date and supporting text when the LLM is enabled. Otherwise require review. | Optional Groq structured LLM call; Python validation |
| Choose | Select reminder, promise, dispute, document or payment-evidence handling. | Deterministic Python policy routed by LangGraph |
| Approve | Review & approve pauses for a person. Automatic processing allows eligible actions within policy. | LangGraph interrupt/resume; up to three new automatic reminders per run |
| Act | Send email, record a promise, inspect controlled documents or match synthetic payment evidence. | Resend and allowlisted Python tools |
| Save and continue | Persist the outcome and next step. Replies, approvals or explicit due-promise checks continue the case. | Supabase checkpoints, tool receipts and SSE |

The LLM assists with language; Python validates financial facts and controls actions. A payment claim is not payment proof. Source AR stays unchanged. Follow-ups use an explicit simulation date and check, rather than an always-running scheduler.
