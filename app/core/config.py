from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv
import yaml

load_dotenv()


class ConfigurationError(RuntimeError):
    """Raised when YAML/environment configuration is missing or invalid."""


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ConfigurationError(f"YAML root must be an object: {path}")
    return data


def _env_optional(name: str | None) -> str | None:
    if not name:
        return None
    value = os.getenv(name, "").strip()
    return value or None


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    provider: str
    host: str
    port: int
    public_base_url: str
    log_level: str
    admin_api_key: str | None
    gateway_path: str

    jwt_enabled: bool
    jwt_issuer: str | None
    jwt_audience: str | None
    jwt_jwks_url: str | None
    jwt_algorithms: list[str]
    jwt_tenant_claim: str

    clients_directory: Path

    @classmethod
    def from_yaml(cls, path: str | Path = "config/app.yaml") -> "AppSettings":
        path = Path(path)
        data = _load_yaml(path)

        app = data.get("app") or {}
        management = data.get("management_api") or {}
        gateway = data.get("gateway") or {}
        auth = gateway.get("authentication") or {}
        jwt = auth.get("jwt") or {}
        clients = data.get("clients") or {}

        try:
            port = int(app.get("port", 8000))
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("app.port must be an integer.") from exc

        if not 1 <= port <= 65535:
            raise ConfigurationError("app.port must be between 1 and 65535.")

        gateway_path = str(gateway.get("public_path", "/mcp")).strip()
        if not gateway_path.startswith("/"):
            gateway_path = "/" + gateway_path

        mode = str(auth.get("mode", "opaque_token")).strip().lower()
        if mode not in {"opaque_token", "jwt"}:
            raise ConfigurationError(
                "gateway.authentication.mode must be 'opaque_token' or 'jwt'."
            )

        jwt_enabled = mode == "jwt" or bool(jwt.get("enabled", False))
        jwt_issuer = _env_optional(jwt.get("issuer_env"))
        jwt_audience = _env_optional(jwt.get("audience_env"))
        jwt_jwks_url = _env_optional(jwt.get("jwks_url_env"))

        if jwt_enabled:
            missing = []
            if not jwt_issuer:
                missing.append(str(jwt.get("issuer_env") or "JWT issuer"))
            if not jwt_audience:
                missing.append(str(jwt.get("audience_env") or "JWT audience"))
            if not jwt_jwks_url:
                missing.append(str(jwt.get("jwks_url_env") or "JWKS URL"))
            if missing:
                raise ConfigurationError(
                    "JWT authentication is enabled but missing environment values for: "
                    + ", ".join(missing)
                )

        configured_dir = Path(str(clients.get("directory", "config/clients")))
        if not configured_dir.is_absolute():
            configured_dir = Path.cwd() / configured_dir

        admin_api_key = None
        if bool(management.get("enabled", True)):
            admin_api_key = _env_optional(management.get("admin_api_key_env"))

        return cls(
            app_name=str(app.get("name", "ZenBiz MCP Manager")).strip(),
            provider=str(app.get("provider", "Zen Business Solutions")).strip(),
            host=str(app.get("host", "0.0.0.0")).strip(),
            port=port,
            public_base_url=str(
                app.get("public_base_url", "http://localhost:8000")
            ).strip().rstrip("/"),
            log_level=str(app.get("log_level", "INFO")).strip().upper(),
            admin_api_key=admin_api_key,
            gateway_path=gateway_path,
            jwt_enabled=jwt_enabled,
            jwt_issuer=jwt_issuer,
            jwt_audience=jwt_audience,
            jwt_jwks_url=jwt_jwks_url,
            jwt_algorithms=[str(x) for x in jwt.get("algorithms", ["RS256"])],
            jwt_tenant_claim=str(jwt.get("tenant_claim", "tenant_id")).strip(),
            clients_directory=configured_dir,
        )
