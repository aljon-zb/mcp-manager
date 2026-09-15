from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.audit import log_tool
from app.core.branding import branded_response
from app.core.models import ClientConfig
from app.integrations.odoo.client import OdooClient
from app.clients.peltierpro.prompts import register_prompts
from app.clients.peltierpro.settings import tool_settings
from app.clients.peltierpro.tools import (
    register_connection_tools,
    register_users_tools,
    register_projects_tools,
    register_crm_tools,
    register_sales_tools,
    register_accounting_tools,
    register_inventory_tools,
    register_contacts_tools,
)


SERVER_INSTRUCTIONS = """
You are the PeltierPro Odoo MCP integration provided by Zen Business Solutions.
Use the available tools only for the connected PeltierPro tenant.
Do not claim access to any other Zen Business Solutions client or MCP tenant.
For write actions, present the resulting record and status clearly to the user.
""".strip()


def build_peltierpro_mcp(client: ClientConfig) -> FastMCP:
    if not client.odoo:
        raise RuntimeError("PeltierPro requires Odoo configuration.")

    settings = tool_settings(client)

    odoo = OdooClient(
        base_url=client.odoo.url,
        database=client.odoo.database,
        api_key=client.odoo.api_key,
        timeout_seconds=client.odoo.request_timeout_seconds,
    )

    mcp = FastMCP(
        "ZenBiz PeltierPro Odoo MCP",
        instructions=SERVER_INSTRUCTIONS,
        stateless_http=True,
        json_response=True,
    )

    def failed(
        tool: str,
        exc: Exception,
        params: dict[str, Any],
    ):
        log_tool(
            tool,
            params,
            success=False,
            error=str(exc),
            client_id=client.id,
        )
        return branded_response(
            {
                "success": False,
                "client": client.name,
                "error": str(exc),
            }
        )

    register_prompts(mcp)
    register_connection_tools(mcp, odoo, settings, failed)
    register_users_tools(mcp, odoo, settings, failed)
    register_projects_tools(mcp, odoo, settings, failed)
    register_crm_tools(mcp, odoo, settings, failed)
    register_sales_tools(mcp, odoo, settings, failed)
    register_accounting_tools(mcp, odoo, settings, failed)
    register_inventory_tools(mcp, odoo, settings, failed)
    register_contacts_tools(mcp, odoo, settings, failed)

    return mcp
