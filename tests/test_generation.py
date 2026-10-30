import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from app.config import settings
from app.knowledge import Knowledge
from app import workflow


@pytest.mark.parametrize('content,mode', [('Page the on-call commander [S1].','openai'),
                                          ('Invented source [S99].','extractive'),
                                          ('Unsupported answer without citations.','extractive')])
def test_generated_citation_guard(tmp_path,monkeypatch,content,mode):
    monkeypatch.setenv('OPENAI_API_KEY','test-key-never-sent')
    monkeypatch.setenv('EMBEDDING_MODE','offline')
    monkeypatch.setenv('QDRANT_PATH',str(tmp_path/'vectors'))
    settings.cache_clear()
    class FakeClient:
        def __init__(self,**kwargs):
            self.chat = NS(completions=NS(create=self.create))
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def create(self,**kwargs): return NS(choices=[NS(message=NS(content=content))])
    monkeypatch.setattr('openai.AsyncOpenAI',FakeClient)
    kb = Knowledge(settings())
    try:
        kb.ingest('escalation.md',Path('samples/escalation.md').read_bytes())
        r = asyncio.run(workflow.make_graph(kb).ainvoke({'question':'What is the P1 escalation policy?', 'top_k':3}))
        assert r['generation_mode'] == mode
        assert '[S99]' not in r['answer']
        if mode == 'extractive': assert '15 minutes' in r['answer']
    finally:
        kb.client.close(); settings.cache_clear()


def test_function_call_cannot_introduce_identifier(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-key-never-sent')
    monkeypatch.setenv('EMBEDDING_MODE','offline')
    monkeypatch.setenv('QDRANT_PATH',str(tmp_path/'vectors'))
    settings.cache_clear()
    class FakeClient:
        def __init__(self,**kwargs): self.chat=NS(completions=NS(create=self.create))
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def create(self,**kwargs):
            if 'tools' in kwargs:
                return NS(choices=[NS(message=NS(tool_calls=[NS(function=NS(name='get_order_status',arguments='{"order_id":"ORD-9999"}'))]))])
            return NS(choices=[NS(message=NS(content='Simulated order is in transit.'))])
    monkeypatch.setattr('openai.AsyncOpenAI',FakeClient)
    calls=[]
    async def fake_call(name,args):
        calls.append((name,args)); return {'id':args['order_id'],'status':'in transit'}
    monkeypatch.setattr(workflow,'call_tool',fake_call)
    kb = Knowledge(settings())
    try:
        r=asyncio.run(workflow.make_graph(kb).ainvoke({'question':'Status of ORD-1003?', 'top_k':3}))
        assert calls == [('get_order_status',{'order_id':'ORD-1003'})]
        assert r['tools'] == ['get_order_status']
    finally:
        kb.client.close(); settings.cache_clear()
