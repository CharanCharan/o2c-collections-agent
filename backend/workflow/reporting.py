"""Frozen per-invoice run outcomes; no attribution from a case's original run ID.

Baseline is saved before graph work. Resume reuses it, including accepted email
persisted before a crash. Later manual approvals/replies are current state only.
"""

def case_snapshot(case):
    w=case.get('workflow') or {}
    mails=[m for m in [case.get('outbound'),*case.get('followups',[])] if m]
    return {'accepted_mail_ids':[m['id'] for m in mails if m['state']=='accepted'],
        'promise':w.get('promise'),'dispute':case.get('collection_status')=='dispute_hold_review_required',
        'status':w.get('status') or case.get('collection_status')}


def case_result(before,case):
    after=case_snapshot(case)
    old=set(before['accepted_mail_ids'])
    initial=case.get('outbound')
    followups=case.get('followups',[])
    return {'initial_mail_ids':[initial['id']] if initial and initial['state']=='accepted' and initial['id'] not in old else [],
        'followup_mail_ids':[m['id'] for m in followups if m['state']=='accepted' and m['id'] not in old],
        'promise_recorded':bool(after['promise'] and after['promise']!=before.get('promise')),
        'dispute_on_hold':after['dispute'],
        'new_dispute_hold':after['dispute'] and not before.get('dispute'),
        'status':after['status']}
