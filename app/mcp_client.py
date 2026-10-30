import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import settings

ALLOWED = {'get_customer', 'get_order_status', 'get_ticket', 'list_customer_tickets'}


async def call_tool(name: str, arguments: dict):
    if name not in ALLOWED:
        raise ValueError('Tool is not permitted')
    cfg = settings()
    # The MCP SDK intentionally inherits only a small default environment.
    # Forward the adapter's two required settings explicitly, including Render secrets.
    params = StdioServerParameters(command=sys.executable, args=['-m', 'app.mcp_server'],
        env={'API_BASE_URL': cfg.api_base_url, 'ENTERPRISE_API_KEY': cfg.enterprise_api_key})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            if result.isError:
                raise RuntimeError('Enterprise tool failed; verify identifier and service availability')
            structured = getattr(result, 'structuredContent', None)
            if structured is not None:
                return structured
            return {'result': [json.loads(c.text) for c in result.content if c.type == 'text']}
