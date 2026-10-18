"""Public-safe job diagnostics. Never persist raw exception/provider bodies."""
import logging
from uuid import uuid4
from fastapi import HTTPException
from ..storage import StorageError, StoreRequestError


def failure(exc,invoice_id,phase):
    code='case_processing_failed'
    message='Invoice processing needs review. Other invoices will still be processed.'
    if isinstance(exc,(StoreRequestError,HTTPException)):
        status=exc.status if isinstance(exc,StoreRequestError) else exc.status_code
        code='case_capacity' if status==429 else 'case_access_or_policy'
        message='Case storage capacity needs owner attention.' if status==429 else 'Case access or policy blocked this operation.'
    elif isinstance(exc,StorageError):
        code=getattr(exc,'code','storage_operation_failed')
        message={'network_unavailable':'The database connection failed during this invoice.',
            'schema_missing':'A required database function is missing; apply the required migrations.',
            'access_denied':'Database access was rejected; the owner must check configuration.',
            'checkpoint_reference_error':'Checkpoint storage rejected a reference. Apply sql/013_checkpoint_repair.sql, then retry failed invoices.',
            'checkpoint_schema_error':'Checkpoint schema needs repair. Apply sql/013_checkpoint_repair.sql.',
            'database_timeout':'The database operation timed out. Check database availability.'}.get(code,'A database operation failed during this invoice. Check schema and database availability.')
    result={'error_id':str(uuid4()),'code':code,'message':message,'phase':phase,'invoice_id':invoice_id,'exception_type':type(exc).__name__}
    if getattr(exc,'operation',None):result['operation']=exc.operation
    for name in ['sqlstate','checkpoint_action']:
        if getattr(exc,name,None):result[name]=getattr(exc,name)
    logging.getLogger(__name__).error('Collection failure error_id=%s code=%s invoice=%s phase=%s operation=%s',
        result['error_id'],code,invoice_id,phase,result.get('operation','-'))
    return result
