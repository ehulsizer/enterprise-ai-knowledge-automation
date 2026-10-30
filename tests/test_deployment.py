from pathlib import Path
import yaml
from app.config import Settings
from app.knowledge import Knowledge


def test_free_render_blueprint():
    blueprint = yaml.safe_load(Path('render.yaml').read_text())
    assert set(blueprint) == {'services'}
    assert len(blueprint['services']) == 1
    service = blueprint['services'][0]
    assert service['type'] == 'web' and service['runtime'] == 'docker'
    assert service['plan'] == 'free' and 'disk' not in service
    assert service['numInstances'] == 1 and 'scaling' not in service
    assert service['autoDeployTrigger'] == 'off'
    assert service['healthCheckPath'] == '/health'
    env = {item['key']:item for item in service['envVars']}
    assert env['APP_API_KEY']['generateValue'] is True
    assert env['ENTERPRISE_API_KEY']['generateValue'] is True
    assert env['MAX_CONCURRENT_QUERIES']['value'] == '1'
    assert env['EMBEDDING_THREADS']['value'] == '1'
    assert env['EMBEDDING_MODE']['value'] == 'fastembed'
    assert env['API_BASE_URL']['value'] == 'http://127.0.0.1:' + env['PORT']['value']
    assert 'QDRANT_URL' not in env and 'QDRANT_API_KEY' not in env
    assert Path(service['dockerfilePath']).is_file()


def test_qdrant_cloud_configuration_still_selects_remote_client(monkeypatch):
    captured = {}
    class RemoteClient:
        def __init__(self, **kwargs): captured.update(kwargs)
        def collection_exists(self, name): return True
    monkeypatch.setattr('app.knowledge.QdrantClient', RemoteClient)
    kb = Knowledge(Settings(embedding_mode='offline', qdrant_url='https://example.qdrant.io',
                            qdrant_api_key='test-secret', qdrant_path='unused-local-path'))
    assert captured == {'url':'https://example.qdrant.io','api_key':'test-secret','timeout':15}
    assert kb.collection == 'knowledge_offline_v1'
