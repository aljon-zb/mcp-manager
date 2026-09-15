from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OdooConfig:
    url: str
    database: str
    api_key: str
    request_timeout_seconds: float = 30.0
    max_results: int = 50


@dataclass(frozen=True)
class ClientConfig:
    id: str
    name: str
    integration: str
    ai_agents: tuple[str, ...]
    enabled: bool
    access_tokens: tuple[str, ...]
    runtime_factory: str
    enabled_tools: tuple[str, ...] = field(default_factory=tuple)
    odoo: OdooConfig | None = None

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "integration": self.integration,
            "ai_agents": list(self.ai_agents),
            "enabled": self.enabled,
            "runtime_factory": self.runtime_factory,
            "enabled_tools": list(self.enabled_tools),
            "mcp_endpoint": "/mcp",
        }
