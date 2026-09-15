from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from starlette.routing import Mount

from app.core.config import AppSettings
from app.core.registry import build_registry_from_yaml
from app.gateway.asgi import MCPGateway
from app.gateway.auth import TenantResolver
from app.gateway.runtime import RuntimeManager


settings = AppSettings.from_yaml("config/app.yaml")

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

registry = build_registry_from_yaml(settings)
resolver = TenantResolver(registry, settings)
runtimes = RuntimeManager(registry)
gateway = MCPGateway(resolver, runtimes)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await runtimes.start()
    try:
        yield
    finally:
        await runtimes.stop()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.app_name,
        "provider": settings.provider,
        "mcp_endpoint": settings.gateway_path,
        "health_endpoint": "/health",
        "management_api": "/api/v1/mcps",
        "configuration": "yaml",
        "configured_clients": len(registry.enabled()),
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "configured_clients": len(registry.enabled()),
    }


def _require_admin(x_admin_api_key: str | None):
    if settings.admin_api_key is None:
        return
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key.")


@app.get("/api/v1/mcps")
async def list_mcps(x_admin_api_key: str | None = Header(default=None)):
    _require_admin(x_admin_api_key)
    return {
        "count": len(registry.all()),
        "items": [client.public_dict() for client in registry.all()],
    }


@app.get("/api/v1/mcps/{client_id}")
async def get_mcp(
    client_id: str,
    x_admin_api_key: str | None = Header(default=None),
):
    _require_admin(x_admin_api_key)
    client = registry.get(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="MCP client not found.")
    return client.public_dict()


@app.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource_metadata():
    if not settings.jwt_enabled or not settings.jwt_issuer:
        return JSONResponse(
            {
                "detail": (
                    "OAuth discovery is not enabled. "
                    "This deployment currently accepts configured Bearer access tokens."
                )
            },
            status_code=404,
        )

    return {
        "resource": f"{settings.public_base_url}{settings.gateway_path}",
        "authorization_servers": [settings.jwt_issuer],
        "bearer_methods_supported": ["header"],
    }


# One public MCP URL. Tenant selection occurs from the presented credential.
app.router.routes.append(Mount(settings.gateway_path, app=gateway))
