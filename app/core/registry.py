from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Iterable

import yaml

from app.core.config import AppSettings, ConfigurationError
from app.core.models import ClientConfig, OdooConfig


class ClientRegistry:
    """In-memory tenant registry loaded from YAML client definitions."""

    def __init__(self, clients: Iterable[ClientConfig]):
        self._clients = {client.id: client for client in clients}
        self._token_index: dict[str, str] = {}

        for client in self._clients.values():
            for token in client.access_tokens:
                if token:
                    self._token_index[self._digest(token)] = client.id

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def all(self) -> list[ClientConfig]:
        return list(self._clients.values())

    def enabled(self) -> list[ClientConfig]:
        return [client for client in self.all() if client.enabled]

    def get(self, client_id: str) -> ClientConfig | None:
        return self._clients.get(client_id)

    def resolve_opaque_token(self, token: str) -> ClientConfig | None:
        digest = self._digest(token)
        for stored_digest, client_id in self._token_index.items():
            if hmac.compare_digest(digest, stored_digest):
                client = self.get(client_id)
                if client and client.enabled:
                    return client
        return None


def _required_env(name: str, client_id: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Client '{client_id}' requires environment variable: {name}"
        )
    return value


def _load_client_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"Client YAML root must be an object: {path}")
    return data


def _parse_client(path: Path) -> ClientConfig:
    data = _load_client_yaml(path)

    client_id = str(data.get("id", "")).strip()
    if not client_id:
        raise ConfigurationError(f"Missing client id in {path}")

    enabled = bool(data.get("enabled", True))
    integration = str(data.get("integration", "")).strip().lower()
    runtime = data.get("runtime") or {}
    auth = data.get("authentication") or {}
    tools = data.get("tools") or {}

    token_envs = auth.get("access_token_envs") or []
    if not isinstance(token_envs, list):
        raise ConfigurationError(
            f"authentication.access_token_envs must be a list in {path}"
        )

    access_tokens: list[str] = []
    if enabled:
        for env_name in token_envs:
            access_tokens.append(_required_env(str(env_name), client_id))

    integration_config = data.get("integration_config") or {}
    odoo = None

    if integration == "odoo":
        if enabled:
            url = _required_env(str(integration_config.get("url_env", "")), client_id)
            database = _required_env(
                str(integration_config.get("database_env", "")), client_id
            )
            api_key = _required_env(
                str(integration_config.get("api_key_env", "")), client_id
            )
        else:
            url = database = api_key = ""

        timeout = float(integration_config.get("request_timeout_seconds", 30))
        max_results = int(integration_config.get("max_results", 50))
        if not 1 <= max_results <= 200:
            raise ConfigurationError(
                f"Client '{client_id}' max_results must be between 1 and 200."
            )

        odoo = OdooConfig(
            url=url.rstrip("/"),
            database=database,
            api_key=api_key,
            request_timeout_seconds=timeout,
            max_results=max_results,
        )

    return ClientConfig(
        id=client_id,
        name=str(data.get("name", client_id)).strip(),
        integration=integration,
        ai_agents=tuple(str(x) for x in (data.get("ai_agents") or [])),
        enabled=enabled,
        access_tokens=tuple(access_tokens),
        runtime_factory=str(runtime.get("factory", client_id)).strip(),
        enabled_tools=tuple(str(x) for x in (tools.get("enabled") or [])),
        odoo=odoo,
    )


def build_registry_from_yaml(settings: AppSettings) -> ClientRegistry:
    directory = settings.clients_directory
    directory.mkdir(parents=True, exist_ok=True)

    clients: list[ClientConfig] = []
    seen_ids: set[str] = set()

    for path in sorted(directory.glob("*.yaml")):
        client = _parse_client(path)
        if client.id in seen_ids:
            raise ConfigurationError(f"Duplicate client id: {client.id}")
        seen_ids.add(client.id)
        clients.append(client)

    for path in sorted(directory.glob("*.yml")):
        client = _parse_client(path)
        if client.id in seen_ids:
            raise ConfigurationError(f"Duplicate client id: {client.id}")
        seen_ids.add(client.id)
        clients.append(client)

    return ClientRegistry(clients)
