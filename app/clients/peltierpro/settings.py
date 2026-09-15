from dataclasses import dataclass

from app.core.models import ClientConfig


@dataclass(frozen=True)
class ToolSettings:
    max_results: int


def tool_settings(client: ClientConfig) -> ToolSettings:
    if not client.odoo:
        raise RuntimeError("PeltierPro requires Odoo configuration.")
    return ToolSettings(max_results=client.odoo.max_results)
