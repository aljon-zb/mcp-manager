from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


# ------------------------------------------------------------
# Project root
# ------------------------------------------------------------
# app/core/config.py
#       ↑ core
#   ↑ app
# ↑ project root
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class ConfigurationError(RuntimeError):
    """Raised when YAML/environment configuration is missing or invalid."""


def _load_yaml(path: str | Path) -> dict:
    """
    Load a YAML configuration file.

    Relative paths are resolved from the project root so this works
    consistently in local development, Docker, and Railway.
    """

    file_path = Path(path)

    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    file_path = file_path.resolve()

    if not file_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {file_path}"
        )

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Invalid YAML configuration: {file_path}"
        ) from exc

    if not isinstance(data, dict):
        raise ConfigurationError(
            f"YAML root must be an object: {file_path}"
        )

    return data


def _env_optional(
    name: str | None,
) -> str | None:
    """
    Resolve an optional environment variable.

    YAML contains the variable name, while Railway/.env contains
    the actual secret value.
    """

    if not name:
        return None

    value = os.getenv(
        str(name),
        "",
    ).strip()

    return value or None


@dataclass(frozen=True)
class AppSettings:
    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    app_name: str
    provider: str
    host: str
    port: int
    public_base_url: str
    log_level: str

    # --------------------------------------------------------
    # Management API
    # --------------------------------------------------------

    admin_api_key: str | None

    # --------------------------------------------------------
    # MCP Gateway
    # --------------------------------------------------------

    gateway_path: str

    # --------------------------------------------------------
    # JWT
    # --------------------------------------------------------

    jwt_enabled: bool
    jwt_issuer: str | None
    jwt_audience: str | None
    jwt_jwks_url: str | None
    jwt_algorithms: list[str]
    jwt_tenant_claim: str

    # --------------------------------------------------------
    # MCP Clients
    # --------------------------------------------------------

    clients_directory: Path

    @classmethod
    def from_yaml(
        cls,
        path: str | Path = "config/app.yaml",
    ) -> "AppSettings":

        # ----------------------------------------------------
        # Resolve app.yaml
        # ----------------------------------------------------

        file_path = Path(path)

        if not file_path.is_absolute():
            file_path = (
                PROJECT_ROOT
                / file_path
            )

        file_path = file_path.resolve()

        data = _load_yaml(
            file_path
        )

        # ----------------------------------------------------
        # Sections
        # ----------------------------------------------------

        app = (
            data.get("app")
            or {}
        )

        management = (
            data.get("management_api")
            or {}
        )

        gateway = (
            data.get("gateway")
            or {}
        )

        auth = (
            gateway.get("authentication")
            or {}
        )

        jwt = (
            auth.get("jwt")
            or {}
        )

        clients = (
            data.get("clients")
            or {}
        )

        # ----------------------------------------------------
        # App port
        #
        # Railway normally injects PORT automatically.
        # Prefer Railway/environment value when available.
        # ----------------------------------------------------

        configured_port = os.getenv(
            "PORT",
            str(
                app.get(
                    "port",
                    8000,
                )
            ),
        )

        try:
            port = int(
                configured_port
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ConfigurationError(
                "Application port must be an integer."
            ) from exc

        if not 1 <= port <= 65535:
            raise ConfigurationError(
                "Application port must be between 1 and 65535."
            )

        # ----------------------------------------------------
        # Host
        # ----------------------------------------------------

        host = str(
            os.getenv(
                "HOST",
                app.get(
                    "host",
                    "0.0.0.0",
                ),
            )
        ).strip()

        # ----------------------------------------------------
        # Public Base URL
        # ----------------------------------------------------

        public_base_url = str(
            os.getenv(
                "PUBLIC_BASE_URL",
                app.get(
                    "public_base_url",
                    "http://localhost:8000",
                ),
            )
        ).strip().rstrip("/")

        # ----------------------------------------------------
        # Log level
        # ----------------------------------------------------

        log_level = str(
            os.getenv(
                "LOG_LEVEL",
                app.get(
                    "log_level",
                    "INFO",
                ),
            )
        ).strip().upper()

        # ----------------------------------------------------
        # Gateway path
        # ----------------------------------------------------

        gateway_path = str(
            gateway.get(
                "public_path",
                "/mcp",
            )
        ).strip()

        if not gateway_path:
            gateway_path = "/mcp"

        if not gateway_path.startswith("/"):
            gateway_path = (
                "/"
                + gateway_path
            )

        # ----------------------------------------------------
        # Authentication mode
        # ----------------------------------------------------

        mode = str(
            auth.get(
                "mode",
                "opaque_token",
            )
        ).strip().lower()

        if mode not in {
            "opaque_token",
            "jwt",
        }:
            raise ConfigurationError(
                "gateway.authentication.mode must be "
                "'opaque_token' or 'jwt'."
            )

        # ----------------------------------------------------
        # JWT configuration
        #
        # JWT is enabled when:
        #
        # mode: jwt
        #
        # OR
        #
        # jwt:
        #   enabled: true
        # ----------------------------------------------------

        jwt_enabled = (
            mode == "jwt"
            or bool(
                jwt.get(
                    "enabled",
                    False,
                )
            )
        )

        jwt_issuer = (
            _env_optional(
                jwt.get(
                    "issuer_env"
                )
            )
        )

        jwt_audience = (
            _env_optional(
                jwt.get(
                    "audience_env"
                )
            )
        )

        jwt_jwks_url = (
            _env_optional(
                jwt.get(
                    "jwks_url_env"
                )
            )
        )

        # ----------------------------------------------------
        # JWT algorithms
        # ----------------------------------------------------

        algorithms_raw = (
            jwt.get(
                "algorithms",
                ["RS256"],
            )
        )

        if not isinstance(
            algorithms_raw,
            list,
        ):
            raise ConfigurationError(
                "gateway.authentication.jwt.algorithms "
                "must be a YAML list."
            )

        jwt_algorithms = [
            str(algorithm).strip()
            for algorithm
            in algorithms_raw
            if str(
                algorithm
            ).strip()
        ]

        if not jwt_algorithms:
            jwt_algorithms = [
                "RS256"
            ]

        # ----------------------------------------------------
        # Tenant claim
        # ----------------------------------------------------

        jwt_tenant_claim = str(
            jwt.get(
                "tenant_claim",
                "tenant_id",
            )
        ).strip()

        if not jwt_tenant_claim:
            jwt_tenant_claim = (
                "tenant_id"
            )

        # ----------------------------------------------------
        # Validate JWT environment only when JWT is enabled.
        #
        # Since you currently use:
        #
        # mode: opaque_token
        #
        # your blank JWT Railway variables are allowed.
        # ----------------------------------------------------

        if jwt_enabled:
            missing = []

            issuer_env = (
                jwt.get(
                    "issuer_env"
                )
            )

            audience_env = (
                jwt.get(
                    "audience_env"
                )
            )

            jwks_url_env = (
                jwt.get(
                    "jwks_url_env"
                )
            )

            if not jwt_issuer:
                missing.append(
                    str(
                        issuer_env
                        or "JWT issuer"
                    )
                )

            if not jwt_audience:
                missing.append(
                    str(
                        audience_env
                        or "JWT audience"
                    )
                )

            if not jwt_jwks_url:
                missing.append(
                    str(
                        jwks_url_env
                        or "JWKS URL"
                    )
                )

            if missing:
                raise ConfigurationError(
                    "JWT authentication is enabled "
                    "but missing environment values for: "
                    + ", ".join(
                        missing
                    )
                )

        # ----------------------------------------------------
        # Client configuration directory
        # ----------------------------------------------------

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

        configured_dir = (
            configured_dir.resolve()
        )

        if not configured_dir.exists():
            raise ConfigurationError(
                "Client configuration directory "
                f"not found: {configured_dir}"
            )

        # ----------------------------------------------------
        # Management API
        # ----------------------------------------------------

        admin_api_key = None

        management_enabled = bool(
            management.get(
                "enabled",
                True,
            )
        )

        if management_enabled:
            admin_env_name = (
                management.get(
                    "admin_api_key_env",
                    "ADMIN_API_KEY",
                )
            )

            admin_api_key = (
                _env_optional(
                    str(
                        admin_env_name
                    )
                )
            )

        # ----------------------------------------------------
        # Return settings
        # ----------------------------------------------------

        return cls(
            app_name=str(
                app.get(
                    "name",
                    "ZenBiz MCP Manager",
                )
            ).strip(),

            provider=str(
                app.get(
                    "provider",
                    "Zen Business Solutions",
                )
            ).strip(),

            host=host,

            port=port,

            public_base_url=(
                public_base_url
            ),

            log_level=(
                log_level
            ),

            admin_api_key=(
                admin_api_key
            ),

            gateway_path=(
                gateway_path
            ),

            jwt_enabled=(
                jwt_enabled
            ),

            jwt_issuer=(
                jwt_issuer
            ),

            jwt_audience=(
                jwt_audience
            ),

            jwt_jwks_url=(
                jwt_jwks_url
            ),

            jwt_algorithms=(
                jwt_algorithms
            ),

            jwt_tenant_claim=(
                jwt_tenant_claim
            ),

            clients_directory=(
                configured_dir
            ),
        )
