"""Stdio MCP adapter. stdout is reserved exclusively for MCP protocol messages."""
import httpx
from mcp.server.fastmcp import FastMCP
from app.config import settings

server = FastMCP('Synthetic Enterprise Tools')


async def get(path, params=None):
    cfg = settings()
    async with httpx.AsyncClient(base_url=cfg.api_base_url, timeout=10,
                                 headers={'X-Enterprise-Key': cfg.enterprise_api_key}) as client:
        r = await client.get('/enterprise/' + path, params=params)
        r.raise_for_status()
        return r.json()


@server.tool()
async def get_customer(customer_id: str) -> dict:
    """Read a synthetic customer by CUST identifier."""
    return await get(f'customers/{customer_id}')


@server.tool()
async def get_order_status(order_id: str) -> dict:
    """Read synthetic order status by ORD identifier."""
    return await get(f'orders/{order_id}')


@server.tool()
async def get_ticket(ticket_id: str) -> dict:
    """Read a synthetic service ticket by TKT identifier."""
    return await get(f'tickets/{ticket_id}')


@server.tool()
async def list_customer_tickets(customer_id: str, status: str = 'open') -> list[dict]:
    """List a customer's synthetic service tickets with an explicit status filter."""
    return await get(f'customers/{customer_id}/tickets', {'status': status})


if __name__ == '__main__':
    server.run(transport='stdio')
