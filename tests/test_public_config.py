from app.core.models import ClientConfig, OdooConfig


def test_public_dict_never_returns_secrets():
    client = ClientConfig(
        id="peltierpro",
        name="PeltierPro",
        integration="odoo",
        ai_agents=("claude", "chatgpt"),
        enabled=True,
        access_tokens=("mcp-secret",),
        odoo=OdooConfig(
            url="https://example.com",
            database="db",
            api_key="odoo-secret",
        ),
    )

    data = client.public_dict()
    serialized = str(data)

    assert "mcp-secret" not in serialized
    assert "odoo-secret" not in serialized
