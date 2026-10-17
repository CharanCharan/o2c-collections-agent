"""Business operations. These functions do the work; they do not update the UI.

The POC uses a trained synthetic-data risk model, transparent policy score and
reminder template. LLMs are a later milestone. Monetary calculations use Decimal; JSON amounts are decimal strings.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from . import risk_model
from .models import ReceivablesSnapshot


POLICY_VERSION = "collections-policy-v1"
TEMPLATE_VERSION = "reminder-template-v1"


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


@dataclass
class Context:
    raw: dict = field(default_factory=dict)
    snapshot: ReceivablesSnapshot | None = None
    invoices: list[dict] = field(default_factory=list)
    source_sha256: str = ""
    model: dict | None = None
    models: dict = field(default_factory=dict)
    drafting: dict = field(default_factory=dict)


def ingest(context: Context, source: dict) -> dict:
    # Supabase returns an atomic settings/invoice snapshot. Canonical JSON bytes
    # provide a reproducible hash; there is no local file read or fallback.
    content = json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(content) > 1_000_000:
        raise ValueError("Demo source exceeds the 1 MB limit")
    context.raw = json.loads(content)
    context.source_sha256 = hashlib.sha256(content).hexdigest()
    return {
        "message": "Read the synthetic invoice snapshot directly from Supabase tables.",
        "source": "Supabase: ca_demo_settings + ca_invoices",
        "source_sha256": context.source_sha256,
        "bytes_read": len(content),
    }


def validate(context: Context) -> dict:
    snapshot = ReceivablesSnapshot.model_validate(context.raw)
    context.snapshot = snapshot
    for invoice in snapshot.invoices:
        days = max(0, (snapshot.as_of_date - invoice.due).days)
        if invoice.amount == 0:
            eligible, action = False, "No balance"
        elif invoice.disputed:
            eligible, action = False, "Pause · dispute"
        elif days == 0:
            eligible, action = False, "Not overdue"
        else:
            eligible, action = True, "Awaiting assessment"
        context.invoices.append({
            "id": invoice.id,
            "customer": invoice.customer,
            "segment": invoice.segment,
            "amount": money(invoice.amount),
            "due": invoice.due.isoformat(),
            "days": days,
            "days_to_due": max(0, (invoice.due - snapshot.as_of_date).days),
            "lifecycle": "settled" if invoice.amount == 0 else "overdue" if days > 0 else "pre_due" if invoice.due > snapshot.as_of_date else "due_today",
            "preventive_eligible": invoice.amount > 0 and not invoice.disputed and (invoice.due - snapshot.as_of_date).days == 7,
            "dispute": invoice.disputed,
            "eligible": eligible,
            "action": action,
            "score": None,
            "level": "pending",
            "reasons": [],
            "prediction": None,
            "draft": None,
            "contacted": False,
        })
    return {
        "message": f"Validated {len(context.invoices)} unique invoices in {snapshot.currency}.",
        "validated_count": len(context.invoices),
        "as_of_date": snapshot.as_of_date.isoformat(),
        "currency": snapshot.currency,
    }


def assess(context: Context) -> dict:
    """Policy score: aging up to 40 + historic lateness up to 40 + broken promise 20.

    A 75/100 score is collection urgency, not a 75% probability of late payment.
    New customers get zero history points; missing history is disclosed below.
    """
    history = {invoice.id: invoice for invoice in context.snapshot.invoices}
    for row in context.invoices:
        invoice = history[row["id"]]
        if row['days'] == 0:
            row['score'], row['level'] = None, 'not_due'
            row['reasons'] = ['Not overdue: overdue collection urgency does not apply.']
            if invoice.disputed:
                row['reasons'].append('Active dispute: reminders paused regardless of predicted risk.')
            continue
        aging = Decimal(min(row["days"], 90)) * Decimal(40) / Decimal(90)
        lateness = (
            Decimal(invoice.late_payments) * Decimal(40) / invoice.previous_invoices
            if invoice.previous_invoices else Decimal(0)
        )
        promise = Decimal(20 if invoice.broken_promises else 0)
        score = int((aging + lateness + promise).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        row["score"] = score
        row["level"] = "high" if score >= 65 else "med" if score >= 35 else "low"
        row["reasons"] = [
            f"{row['days']} days overdue: {aging:.1f}/40 aging points.",
            (f"{invoice.late_payments}/{invoice.previous_invoices} previous invoices paid late: "
             f"{lateness:.1f}/40 history points." if invoice.previous_invoices else
             "No previous invoice history; 0 history points assigned, with limited evidence."),
            f"{invoice.broken_promises} broken promises: {promise}/20 points.",
        ]
        if invoice.disputed:
            row["reasons"].append("Active dispute: automated reminder paused regardless of score.")
        if row["eligible"]:
            row["action"] = "Draft reminder" if score >= 35 else "Monitor"
    paused = sum(row["dispute"] for row in context.invoices)
    return {
        "message": f"Assessed collection urgency with {POLICY_VERSION}; {paused} disputed invoice(s) paused.",
        "policy_version": POLICY_VERSION,
        "score_type": "rule_based_urgency_not_probability",
        "paused_count": paused,
    }


def predict(context: Context) -> dict:
    # Freeze both artifacts for the run, even if source has no pre-due examples yet.
    model = risk_model.load_model()
    preventive = risk_model.load_model(stage='pre_due')
    context.model = risk_model.model_card(model)  # Backward-compatible overdue card.
    context.models = {'overdue': context.model, 'pre_due': risk_model.model_card(preventive)}
    history = {invoice.id: invoice for invoice in context.snapshot.invoices}
    counts = {'overdue': 0, 'pre_due': 0, 'not_scored': 0}
    for row in context.invoices:
        invoice = history[row['id']]
        if invoice.amount == 0:
            prediction = {'status': 'not_scored', 'reason': 'No outstanding balance.'}
        elif row['days'] > 0:
            prediction = risk_model.predict_invoice(model, row['days'], invoice.amount,
                invoice.previous_invoices, invoice.late_payments, invoice.broken_promises)
            prediction['horizon_date'] = (context.snapshot.as_of_date + timedelta(days=30)).isoformat()
            counts['overdue'] += 1
        elif row['days_to_due'] == 7:
            prediction = risk_model.predict_pre_due(preventive, invoice.amount,
                invoice.previous_invoices, invoice.late_payments, invoice.broken_promises)
            prediction['horizon_date'] = invoice.due.isoformat()
            prediction['outcome_check_date'] = (invoice.due + timedelta(days=1)).isoformat()
            counts['pre_due'] += 1
            if not invoice.disputed:
                row['action'] = 'Review before due'
                row['reasons'].append('Seven-day checkpoint: review preventive risk before the invoice is overdue.')
        else:
            prediction = {'status': 'not_scored',
                'reason': 'Pre-due model applies exactly seven days before due; no matching historical snapshot is available.'}
            if not invoice.disputed:
                row['action'] = 'Await scoring window' if row['days_to_due'] > 7 else 'Outside scoring window'
        if prediction['status'] == 'scored':
            prediction['scored_as_of'] = context.snapshot.as_of_date.isoformat()
        else:
            counts['not_scored'] += 1
        row['prediction'] = prediction
    return {'message': f"Predicted overdue risk for {counts['pre_due']} pre-due invoice(s) and 30-day persistence for {counts['overdue']} overdue invoice(s).",
            'model': context.model, 'models': context.models,
            'scored_count': counts['overdue'] + counts['pre_due'], 'counts': counts,
            'limitation': risk_model.LIMITATION,
            'interpretation': 'Different targets and stages; neither model is independent proof of the other.'}


def prioritize(context: Context) -> dict:
    for row in context.invoices:
        # Risk-weighted exposure is a ranking index, not expected cash recovery.
        prediction = row['prediction'] or {}
        probability = prediction.get('probability_unpaid_30d', prediction.get('probability_overdue'))
        row['priority_bucket'] = 'overdue' if row['eligible'] else 'pre_due' if row.get('preventive_eligible') else 'none'
        row['priority_index'] = money(Decimal(row['amount']) * Decimal(str(probability))) if probability is not None else '0.00'
    context.invoices.sort(key=lambda row: (
        {'overdue': 0, 'pre_due': 1, 'none': 2}[row['priority_bucket']], -Decimal(row["priority_index"]), -row["days"], row["id"]
    ))
    eligible = [row for row in context.invoices if row["eligible"]]
    preventive = [row for row in context.invoices if row.get("preventive_eligible")]
    top = eligible[0]["customer"] if eligible else "None"
    return {
        "message": f"Ranked {len(eligible)} eligible invoices for recovery; {len(preventive)} separate preventive reviews. Top recovery account: {top}.",
        "eligible_count": len(eligible),
        "preventive_count": len(preventive),
        "ranking_formula": "open_balance * probability within separate overdue and preventive queues; never compare across targets",
        "top_customer": top,
    }


def draft(context: Context) -> dict:
    for row in context.invoices:
        if row["eligible"] and row["score"] >= 35:
            row["draft"] = {
                "subject": f"Payment update requested — invoice {row['id']}",
                "body": (
                    f"Hello {row['customer']} team,\n\n"
                    f"Our records as of {context.snapshot.as_of_date} show invoice {row['id']} "
                    f"for {context.snapshot.currency} {Decimal(row['amount']):,.2f}, due on {row['due']}. "
                    "Could you share an update on expected payment timing? If payment has already "
                    "been arranged or you need supporting details, please let us know.\n\n"
                    "Thank you,\nAccounts Receivable"
                ),
                "template_version": TEMPLATE_VERSION,
                "generation_mode": "template_no_llm",
            }
            row["action"] = "Review draft"
    count = sum(row["draft"] is not None for row in context.invoices)
    return {
        "message": f"Prepared {count} template reminder(s) for review. No email was sent.",
        "draft_count": count,
        "template_version": TEMPLATE_VERSION,
    }


def result_snapshot(context: Context) -> dict:
    rows = context.invoices
    positive = [row for row in rows if Decimal(row["amount"]) > 0]
    overdue = [row for row in positive if row["days"] > 0]
    eligible = [row for row in positive if row["eligible"]]
    total = sum((Decimal(row["amount"]) for row in positive), Decimal(0))
    past_due = sum((Decimal(row["amount"]) for row in overdue), Decimal(0))
    return {
        "workflow_version": "M6",
        "drafting": context.drafting,
        "as_of_date": context.snapshot.as_of_date.isoformat() if context.snapshot else None,
        "currency": context.snapshot.currency if context.snapshot else "USD",
        "source_sha256": context.source_sha256,
        "policy_version": POLICY_VERSION,
        "model": context.model,
        "models": context.models,
        "prediction_mode": "dual_stage_v1",
        "ranking_formula": "open_balance * probability within separate overdue and preventive queues; never compare across targets",
        "invoices": rows,
        "summary": {
            "invoice_count": len(rows),
            "pre_due_count": sum(row.get('lifecycle') == 'pre_due' for row in positive),
            "pre_due_balance": money(sum((Decimal(row['amount']) for row in positive if row.get('lifecycle') == 'pre_due'), Decimal(0))),
            "preventive_review_count": sum(bool(row.get('preventive_eligible')) for row in positive),
            "preventive_review_balance": money(sum((Decimal(row['amount']) for row in positive if row.get('preventive_eligible')), Decimal(0))),
            "open_invoice_count": len(positive),
            "customer_count": len({row['customer'] for row in positive}),
            "open_balance": money(total),
            "past_due_balance": money(past_due),
            "past_due_percent": float((past_due / total * 100).quantize(Decimal("0.1"))) if total else 0,
            "ninety_plus_balance": money(sum((Decimal(row['amount']) for row in positive if row['days'] >= 90), Decimal(0))),
            "ninety_plus_count": sum(row["days"] >= 90 for row in positive),
            "high_urgency_count": sum(row["level"] == "high" for row in eligible),
            "eligible_count": len(eligible),
            "eligible_balance": money(sum((Decimal(row['amount']) for row in eligible), Decimal(0))),
            "disputed_count": sum(row["dispute"] for row in rows),
            "draft_count": sum(row["draft"] is not None for row in rows),
        },
    }
