import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from app.config import settings
from app.main import app
from app import enterprise


def test_platform(tmp_path, monkeypatch):
    monkeypatch.setenv('QDRANT_PATH', str(tmp_path / 'qdrant'))
    monkeypatch.setenv('EMBEDDING_MODE', 'offline')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    settings.cache_clear()
    monkeypatch.setenv('ENTERPRISE_DB_PATH', str(tmp_path / 'records.sqlite'))
    with TestClient(app) as c:
        headers = {'X-API-Key': settings().app_api_key}
        assert c.get('/health').status_code == 200
        assert c.get('/api/status').status_code == 401
        assert c.get('/enterprise/orders/ORD-1003').status_code == 401
        eh = {'X-Enterprise-Key': settings().enterprise_api_key}
        assert c.get('/enterprise/orders/ORD-1003', headers=eh).json()['status'] == 'in transit'
        assert c.get('/enterprise/orders/ORD-9999', headers=eh).status_code == 404
        assert len(c.get('/enterprise/customers/CUST-002/tickets', headers=eh).json()) == 2
        assert c.get('/enterprise/customers/CUST-002/tickets?status=invalid', headers=eh).status_code == 422
        assert c.post('/api/query', headers=headers, json={'question':'hi','top_k':99}).status_code == 422
        result = c.post('/api/query', headers=headers, json={'question':'What is the priority-one P1 escalation policy?'}).json()
        assert result['route'] == 'knowledge'
        assert result['citations'][0]['source'] == 'escalation.md'
        assert '15 minutes' in result['answer']
        assert '[S1]' in result['answer']
        assert 'retrieve:qdrant' in result['trace']
        assert c.post('/api/query', headers=headers, json={'question':'hello there'}).json()['route'] == 'clarify'
        before = c.get('/api/status', headers=headers).json()['chunks']
        for _ in range(2):
            assert c.post('/api/ingest', headers=headers, files={'file':('sample.md',b'Unique sample knowledge. '*50)}).status_code == 200
        after = c.get('/api/status', headers=headers).json()['chunks']
        assert after == before + 1
        assert c.post('/api/ingest', headers=headers, files={'file':('sample.md',b'Replacement content')}).json()['chunks'] == 1
        assert c.get('/api/status', headers=headers).json()['chunks'] == after
        assert c.post('/api/ingest', headers=headers, files={'file':('bad.exe', b'no')}).status_code == 422
        assert c.post('/api/ingest', headers=headers, files={'file':('empty.txt', b'')}).status_code == 422
        assert c.post('/api/ingest', headers=headers, files={'file':('huge.txt', b'x'*(5*1024*1024+1))}).status_code == 413
        pdf = tmp_path/'blank.pdf'
        writer = PdfWriter(); writer.add_blank_page(width=200, height=200)
        writer.write(pdf)
        assert c.post('/api/ingest', headers=headers, files={'file':('blank.pdf',pdf.read_bytes())}).status_code == 422
        assert c.get('/').status_code == 200
        assert c.get('/assets/app.js').status_code == 200
        assert c.get('/assets/unknown').status_code == 404
    settings.cache_clear()


def test_graph_both_and_failure(tmp_path, monkeypatch):
    from app.knowledge import Knowledge
    from app import workflow
    monkeypatch.setenv('QDRANT_PATH', str(tmp_path/'vectors'))
    monkeypatch.setenv('EMBEDDING_MODE', 'offline')
    settings.cache_clear()
    kb = Knowledge(settings())
    try:
        kb.ingest('escalation.md', Path('samples/escalation.md').read_bytes())
        async def fake_call(name,args):
            return {'id':args['ticket_id'], 'priority':'P1','status':'open'}
        monkeypatch.setattr(workflow,'call_tool',fake_call)
        graph = workflow.make_graph(kb)
        r = asyncio.run(graph.ainvoke({'question':'According to policy what happens next for TKT-1001?', 'top_k':4}))
        assert r['route'] == 'both'
        assert r['tools'] == ['get_ticket']
        assert r['trace'].index('tools:mcp:stdio:enterprise-rest') < r['trace'].index('retrieve:qdrant')
        assert r['citations']
        async def fail(*args):
            raise RuntimeError('unavailable')
        monkeypatch.setattr(workflow,'call_tool',fail)
        r = asyncio.run(graph.ainvoke({'question':'Status of ORD-9999', 'top_k':4}))
        assert r['warnings'] and not r['operational_data']
    finally:
        kb.client.close()
        settings.cache_clear()


def test_empty_knowledge(tmp_path, monkeypatch):
    from app.knowledge import Knowledge
    from app.workflow import make_graph
    monkeypatch.setenv('QDRANT_PATH',str(tmp_path/'empty'))
    monkeypatch.setenv('EMBEDDING_MODE','offline')
    settings.cache_clear()
    kb = Knowledge(settings())
    try:
        r = asyncio.run(make_graph(kb).ainvoke({'question':'What is the refund policy?', 'top_k':4}))
        assert not r['citations']
        assert 'does not contain adequate evidence' in r['answer']
    finally:
        kb.client.close()
        settings.cache_clear()
