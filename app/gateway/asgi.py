from __future__ import annotations

from starlette.responses import JSONResponse

from app.gateway.auth import TenantResolver
from app.gateway.runtime import RuntimeManager


class MCPGateway:
    """
    ASGI dispatcher mounted at the single public /mcp URL.

    Authorization: Bearer <token>

    The bearer credential is resolved before any MCP method is executed. The
    request is then forwarded to that tenant's isolated MCP ASGI application.
    """

    def __init__(
        self,
        resolver: TenantResolver,
        runtimes: RuntimeManager,
    ):
        self.resolver = resolver
        self.runtimes = runtimes

    @staticmethod
    def _bearer_token(scope) -> str | None:
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        auth = headers.get("authorization", "").strip()
        if not auth.lower().startswith("bearer "):
            return None
        token = auth[7:].strip()
        return token or None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            response = JSONResponse(
                {"detail": "Unsupported connection type."},
                status_code=400,
            )
            await response(scope, receive, send)
            return

        token = self._bearer_token(scope)
        if not token:
            response = JSONResponse(
                {"detail": "Missing Bearer token."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        client = await self.resolver.resolve(token)
        if not client:
            response = JSONResponse(
                {"detail": "Invalid or unauthorized MCP credential."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        runtime = self.runtimes.get(client.id)
        if not runtime:
            response = JSONResponse(
                {"detail": "MCP runtime is not available."},
                status_code=503,
            )
            await response(scope, receive, send)
            return

        forwarded_scope = dict(scope)
        forwarded_scope["state"] = dict(scope.get("state", {}))
        forwarded_scope["state"]["mcp_client_id"] = client.id
        forwarded_scope["state"]["mcp_client_name"] = client.name

        await runtime.app(forwarded_scope, receive, send)
