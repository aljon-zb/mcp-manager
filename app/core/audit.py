import json
import logging

logger = logging.getLogger("zenbiz_mcp.audit")


def log_tool(
    tool: str,
    parameters=None,
    count=None,
    success: bool = True,
    error=None,
    client_id: str | None = None,
):
    logger.info(
        json.dumps(
            {
                "event": "mcp_tool_call",
                "client_id": client_id,
                "tool": tool,
                "parameters": parameters or {},
                "record_count": count,
                "success": success,
                "error": error,
            },
            default=str,
        )
    )
