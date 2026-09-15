from __future__ import annotations

import asyncio
import time
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.core.config import AppSettings
from app.core.models import ClientConfig
from app.core.registry import ClientRegistry


class TenantResolver:
    """
    Resolve an incoming bearer credential to exactly one MCP client.

    Supported modes:
    1. Opaque per-client access token (MVP / controlled deployments)
    2. JWT issued by a shared authorization server with a tenant claim

    This lets every AI client call the same public /mcp URL.
    """

    def __init__(
        self,
        registry: ClientRegistry,
        settings: AppSettings,
    ):
        self.registry = registry
        self.settings = settings
        self.jwks = (
            PyJWKClient(settings.jwt_jwks_url, cache_keys=True)
            if settings.jwt_enabled and settings.jwt_jwks_url
            else None
        )

    async def resolve(self, token: str) -> ClientConfig | None:
        client = self.registry.resolve_opaque_token(token)
        if client:
            return client

        if not self.settings.jwt_enabled or not self.jwks:
            return None

        return await asyncio.to_thread(self._resolve_jwt_sync, token)

    def _resolve_jwt_sync(self, token: str) -> ClientConfig | None:
        try:
            signing_key = self.jwks.get_signing_key_from_jwt(token).key
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key,
                algorithms=self.settings.jwt_algorithms,
                issuer=self.settings.jwt_issuer,
                audience=self.settings.jwt_audience,
                options={
                    "require": ["exp", "iss"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except (PyJWTError, Exception):
            return None

        exp = claims.get("exp")
        if exp is not None and int(exp) <= int(time.time()):
            return None

        tenant_id = claims.get(self.settings.jwt_tenant_claim)
        if not tenant_id:
            return None

        client = self.registry.get(str(tenant_id))
        if not client or not client.enabled:
            return None

        return client
