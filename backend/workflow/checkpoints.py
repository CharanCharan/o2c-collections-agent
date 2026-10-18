"""Async LangGraph saver over the existing private Supabase RPC adapter.

Stores real checkpoints AND pending writes. No pickle, ephemeral file or memory
fallback. Retains eight recent checkpoints per case; case audit is separate.
SQL014 stores pending writes independently: LangGraph may persist them before
the corresponding checkpoint save finishes. No in-memory save-order fallback.
"""
import base64
from langgraph.checkpoint.base import BaseCheckpointSaver,CheckpointTuple,WRITES_IDX_MAP,get_checkpoint_metadata
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class SupabaseSaver(BaseCheckpointSaver):
    def __init__(self,store):
        super().__init__(serde=JsonPlusSerializer(pickle_fallback=False))
        self.store=store

    def pack(self,value):
        kind,data=self.serde.dumps_typed(value)
        return [kind,base64.b64encode(data).decode()]

    def unpack(self,value):
        return self.serde.loads_typed((value[0],base64.b64decode(value[1])))

    def config(self,case,ns,checkpoint=None):
        result={'thread_id':case,'checkpoint_ns':ns}
        if checkpoint:result['checkpoint_id']=checkpoint
        return {'configurable':result}

    async def aget_tuple(self,config):
        c=config['configurable'];case=c['thread_id'];ns=c.get('checkpoint_ns','')
        row=await self.store.rpc('ca_checkpoint',{'p_action':'get','p_case_id':case,'p_namespace':ns,'p_checkpoint_id':c.get('checkpoint_id')})
        if row is None:return None
        data=row['data']
        return CheckpointTuple(config=self.config(case,ns,row['checkpoint_id']),
            checkpoint=self.unpack(data['checkpoint']),metadata=self.unpack(data['metadata']),
            parent_config=self.config(case,ns,row['parent_id']) if row['parent_id'] else None,
            pending_writes=[(w['task_id'],w['channel'],self.unpack(w['value'])) for w in row['writes']])

    async def aput(self,config,checkpoint,metadata,new_versions):
        c=config['configurable'];case=c['thread_id'];ns=c.get('checkpoint_ns','')
        await self.store.rpc('ca_checkpoint',{'p_action':'put','p_case_id':case,'p_namespace':ns,'p_checkpoint_id':checkpoint['id'],
            'p_data':{'checkpoint':self.pack(checkpoint),'metadata':self.pack(get_checkpoint_metadata(config,metadata)),'parent_id':c.get('checkpoint_id')}})
        return self.config(case,ns,checkpoint['id'])

    async def aput_writes(self,config,writes,task_id,task_path=''):
        c=config['configurable']
        await self.store.rpc('ca_checkpoint',{'p_action':'writes','p_case_id':c['thread_id'],'p_namespace':c.get('checkpoint_ns',''),
            'p_checkpoint_id':c['checkpoint_id'],'p_data':[{'task_id':task_id,'idx':WRITES_IDX_MAP.get(channel,i),
                'channel':channel,'value':self.pack(value),'task_path':task_path} for i,(channel,value) in enumerate(writes)]})
