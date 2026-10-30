from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app


def test_ephemeral_rebuild_and_existing_store_startup(tmp_path, monkeypatch):
    monkeypatch.setenv('EMBEDDING_MODE', 'offline')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('QDRANT_URL', raising=False)
    monkeypatch.setenv('SAMPLE_DOCUMENTS_PATH', str(Path('samples').resolve()))
    monkeypatch.setenv('MAX_CONCURRENT_QUERIES', '1')
    counts = []
    try:
        # Fresh runtime-b models total filesystem loss; revisiting runtime-a
        # verifies idempotency when files happen to survive a restart.
        for name in ('runtime-a', 'runtime-b', 'runtime-a'):
            runtime = tmp_path / name
            monkeypatch.setenv('ENTERPRISE_DB_PATH', str(runtime / 'enterprise.sqlite3'))
            monkeypatch.setenv('QDRANT_PATH', str(runtime / 'qdrant'))
            settings.cache_clear()
            with TestClient(app) as client:
                headers = {'X-API-Key': settings().app_api_key}
                eh = {'X-Enterprise-Key': settings().enterprise_api_key}
                assert client.get('/health').json()['status'] == 'ok'
                counts.append(client.get('/api/status', headers=headers).json()['chunks'])
                assert client.get('/enterprise/orders/ORD-1003', headers=eh).json()['status'] == 'in transit'
                assert len(client.get('/enterprise/customers/CUST-002/tickets?status=open', headers=eh).json()) == 2
                answer = client.post('/api/query', headers=headers,
                    json={'question':'What is the priority-one P1 escalation policy?'}).json()
                assert answer['citations'][0]['source'] == 'escalation.md'
                assert '15 minutes' in answer['answer']
        assert counts[0] > 0 and counts == [counts[0]] * 3
    finally:
        settings.cache_clear()


def test_missing_repository_samples_fail_startup(tmp_path, monkeypatch):
    monkeypatch.setenv('EMBEDDING_MODE', 'offline')
    monkeypatch.setenv('QDRANT_PATH', str(tmp_path / 'qdrant'))
    monkeypatch.setenv('ENTERPRISE_DB_PATH', str(tmp_path / 'enterprise.sqlite3'))
    samples = tmp_path / 'empty-samples'
    samples.mkdir()
    monkeypatch.setenv('SAMPLE_DOCUMENTS_PATH', str(samples))
    settings.cache_clear()
    try:
        with pytest.raises(ValueError, match='repository-managed sample'):
            with TestClient(app):
                pass
        (samples / 'policy.txt').write_text('Refund policy requires billing approval.')
        with TestClient(app) as client:
            response = client.get('/api/status', headers={'X-API-Key':settings().app_api_key})
            assert response.json()['chunks'] == 1
    finally:
        settings.cache_clear()
