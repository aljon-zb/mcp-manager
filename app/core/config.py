from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class ConfigurationError(RuntimeError):
    pass


def _load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)

    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    if not file_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {file_path}"
        )

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Invalid YAML configuration: {file_path}"
        ) from exc

    if not isinstance(data, dict):
        raise ConfigurationError(
            f"YAML root must be an object/map: {file_path}"
        )

    return data


def get_env(
    name: str,
    default: str | None = None,
    required: bool = False,
) -> str | None:
    value = os.getenv(name, default)

    if required and (
        value is None
        or str(value).strip() == ""
    ):
        raise ConfigurationError(
            f"Missing required environment variable: {name}"
        )

    return value


def get_env_bool(
    name: str,
    default: bool = False,
) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    return normalized in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_env_int(
    name: str,
    default: int,
) -> int:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(
            f"Environment variable {name} must be an integer"
        ) from exc


@dataclass(slots=True)
class AppSettings:
    name: str
    provider: str
    host: str
    port: int
    public_base_url: str
    log_level: str

    gateway_path: str
    authentication_mode: str

    clients_directory: Path

    admin_api_key: str | None

    jwt_issuer: str | None
    jwt_audience: str | None
    jwt_jwks_url: str | None

    @classmethod
    def from_yaml(
        cls,
        path: str | Path = "config/app.yaml",
    ) -> "AppSettings":
        file_path = Path(path)

        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path

        data = _load_yaml(file_path)

        app = data.get("app", {})
        gateway = data.get("gateway", {})
        authentication = gateway.get(
            "authentication",
            {},
        )
        clients = data.get("clients", {})

        configured_dir = Path(
            str(
                clients.get(
                    "directory",
                    "config/clients",
                )
            )
        )

        if not configured_dir.is_absolute():
            configured_dir = (
                PROJECT_ROOT
                / configured_dir
            )

        configured_dir = configured_dir.resolve()

        app_name = str(
            app.get(
                "name",
                "ZenBiz MCP Manager",
            )
        )

        provider = str(
            app.get(
                "provider",
                "Zen Business Solutions",
            )
        )

        host = str(
            os.getenv(
                "HOST",
                app.get(
                    "host",
                    "0.0.0.0",
                ),
            )
        )

        port_value = os.getenv(
            "PORT",
            str(
                app.get(
                    "port",
                    8000,
                )
            ),
        )

        try:
            port = int(port_value)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ConfigurationError(
                "Application port must be an integer"
            ) from exc

        public_base_url = str(
            os.getenv(
                "PUBLIC_BASE_URL",
                app.get(
                    "public_base_url",
                    "http://localhost:8000",
                ),
            )
        ).rstrip("/")

        log_level = str(
            os.getenv(
                "LOG_LEVEL",
                app.get(
                    "log_level",
                    "INFO",
                ),
            )
        ).upper()

        gateway_path = str(
            gateway.get(
                "public_path",
                "/mcp",
            )
        )

        if not gateway_path.startswith("/"):
            gateway_path = (
                "/"
                + gateway_path
            )

        authentication_mode = str(
            authentication.get(
                "mode",
                "opaque_token",
            )
        ).strip().lower()

        supported_auth_modes = {
            "opaque_token",
            "jwt",
        }

        if (
            authentication_mode
            not in supported_auth_modes
        ):
            raise ConfigurationError(
                "Unsupported gateway authentication mode: "
                f"{authentication_mode}"
            )

        admin_api_key = get_env(
            "ADMIN_API_KEY"
        )

        jwt_issuer = get_env(
            "GATEWAY_JWT_ISSUER"
        )

        jwt_audience = get_env(
            "GATEWAY_JWT_AUDIENCE"
        )

        jwt_jwks_url = get_env(
            "GATEWAY_JWT_JWKS_URL"
        )

        if authentication_mode == "jwt":
            missing = []

            if not jwt_issuer:
                missing.append(
                    "GATEWAY_JWT_ISSUER"
                )

            if not jwt_audience:
                missing.append(
                    "GATEWAY_JWT_AUDIENCE"
                )

            if not jwt_jwks_url:
                missing.append(
                    "GATEWAY_JWT_JWKS_URL"
                )

            if missing:
                raise ConfigurationError(
                    "JWT authentication is enabled "
                    "but the following environment "
                    "variables are missing: "
                    + ", ".join(missing)
                )

        return cls(
            name=app_name,
            provider=provider,
            host=host,
            port=port,
            public_base_url=public_base_url,
            log_level=log_level,
            gateway_path=gateway_path,
            authentication_mode=authentication_mode,
            clients_directory=configured_dir,
            admin_api_key=admin_api_key,
            jwt_issuer=jwt_issuer,
            jwt_audience=jwt_audience,
            jwt_jwks_url=jwt_jwks_url,
        )
