# ZenBiz MCP Manager — YAML Configuration Edition

A Python/FastAPI multi-client MCP gateway. All AI clients connect to one public MCP endpoint:

```text
https://zenbusinesssolutions.com/mcp
```

The presented Bearer token/JWT identifies the tenant internally. You do not expose `/peltierpro/mcp`, `/hexa/mcp`, etc.

## Configuration model

The project separates **structure** from **secrets**:

- `config/app.yaml` — application/gateway behavior.
- `config/clients/*.yaml` — tenant definitions, tools, integrations, runtime factory, non-secret options.
- `.env` / Railway variables / Docker secrets — actual tokens, API keys and deployment secrets.

Do not put Odoo API keys or MCP bearer tokens directly in YAML. YAML stores the **environment variable name** that contains the secret.

## PeltierPro

The first tenant is:

```text
config/clients/peltierpro.yaml
```

It references these secrets:

```env
PELTIERPRO_MCP_ACCESS_TOKEN=...
PELTIERPRO_ODOO_URL=...
PELTIERPRO_ODOO_DATABASE=...
PELTIERPRO_ODOO_API_KEY=...
```

## Run locally

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Useful URLs:

```text
http://localhost:8000/
http://localhost:8000/health
http://localhost:8000/api/v1/mcps
http://localhost:8000/mcp
```

`/mcp` is an MCP protocol endpoint and should be used through an MCP client, not as a normal browser page.

## Adding another MCP/client

1. Create `config/clients/hexa.yaml`.
2. Define its identity, integration, enabled tools and secret environment variable names.
3. Create its Python MCP runtime under `app/clients/hexa/` if its tool/runtime implementation differs.
4. Register its factory in `app/gateway/runtime.py`.
5. Add the referenced secret values to `.env`/Railway/container environment.

The external endpoint remains `/mcp`.

## Why YAML + environment variables?

YAML is ideal for tenant metadata and configuration that your future Vue admin panel can eventually generate. Environment variables remain better for secrets because they can be injected by Railway/Docker/CI without committing sensitive credentials to Git.
# mcp-manager
