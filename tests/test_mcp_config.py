import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from app.config import settings
from app import mcp_client


def test_mcp_receives_configured_backend_and_key(monkeypatch):
    monkeypatch.setenv('API_BASE_URL', 'http://127.0.0.1:9876')
    monkeypatch.setenv('ENTERPRISE_API_KEY', 'isolated-test-key')
    settings.cache_clear()
    captured = {}
    @asynccontextmanager
    async def stdio(params):
        captured.update(params.env)
        yield (None, None)
    class Session:
        def __init__(self, *args): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def initialize(self): pass
        async def call_tool(self, name, arguments):
            return SimpleNamespace(isError=False, structuredContent={'status':'in transit'})
    monkeypatch.setattr(mcp_client, 'stdio_client', stdio)
    monkeypatch.setattr(mcp_client, 'ClientSession', Session)
    try:
        result = asyncio.run(mcp_client.call_tool('get_order_status', {'order_id':'ORD-1003'}))
        assert result['status'] == 'in transit'
        assert captured == {'API_BASE_URL':'http://127.0.0.1:9876', 'ENTERPRISE_API_KEY':'isolated-test-key'}
    finally:
        settings.cache_clear()
