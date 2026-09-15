from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Callable

from app.core.models import ClientConfig
from app.core.registry import ClientRegistry
from app.clients.peltierpro.server import build_peltierpro_mcp


@dataclass
class ClientRuntime:
    client: ClientConfig
    mcp: Any
    app: Any


MCPFactory = Callable[[ClientConfig], Any]


class RuntimeManager:
    """Creates one isolated FastMCP runtime for every enabled YAML tenant."""

    def __init__(self, registry: ClientRegistry):
        self.registry = registry
        self._runtimes: dict[str, ClientRuntime] = {}
        self._stack: contextlib.AsyncExitStack | None = None
        self._factories: dict[str, MCPFactory] = {
            "peltierpro": build_peltierpro_mcp,
        }

    def register_factory(self, name: str, factory: MCPFactory) -> None:
        self._factories[name] = factory

    async def start(self):
        self._stack = contextlib.AsyncExitStack()
        await self._stack.__aenter__()

        for client in self.registry.enabled():
            await self._create_runtime(client)

    async def stop(self):
        if self._stack:
            await self._stack.aclose()
            self._stack = None
        self._runtimes.clear()

    async def _create_runtime(self, client: ClientConfig) -> ClientRuntime:
        if client.id in self._runtimes:
            return self._runtimes[client.id]

        factory = self._factories.get(client.runtime_factory)
        if factory is None:
            raise RuntimeError(
                f"No MCP runtime factory '{client.runtime_factory}' registered "
                f"for client '{client.id}'."
            )

        mcp = factory(client)
        mcp.settings.streamable_http_path = "/"
        mcp_app = mcp.streamable_http_app()

        if not self._stack:
            raise RuntimeError("RuntimeManager.start() must be called first.")

        await self._stack.enter_async_context(mcp.session_manager.run())

        runtime = ClientRuntime(client=client, mcp=mcp, app=mcp_app)
        self._runtimes[client.id] = runtime
        return runtime

    def get(self, client_id: str) -> ClientRuntime | None:
        return self._runtimes.get(client_id)
