from app.core.models import ClientConfig
from app.core.registry import ClientRegistry


def test_opaque_token_resolves_correct_client():
    registry = ClientRegistry(
        [
            ClientConfig(
                id="peltierpro",
                name="PeltierPro",
                integration="odoo",
                ai_agents=("claude",),
                enabled=True,
                access_tokens=("secret-a",),
            ),
            ClientConfig(
                id="hexa",
                name="Hexa",
                integration="example",
                ai_agents=("chatgpt",),
                enabled=True,
                access_tokens=("secret-b",),
            ),
        ]
    )

    assert registry.resolve_opaque_token("secret-a").id == "peltierpro"
    assert registry.resolve_opaque_token("secret-b").id == "hexa"
    assert registry.resolve_opaque_token("wrong") is None
