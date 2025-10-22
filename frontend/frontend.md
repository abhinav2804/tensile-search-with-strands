# Frontend Portal and Data Pipeline

This folder contains the zero‑code upload portal (Flask) and the enhanced data pipeline that turns raw files into a ready‑to‑query Elasticsearch index, locally or on a remote VM, with optional MCP integration for LLM‑driven search.

## What this component does

- Accepts CSV/JSON uploads and a small list of example queries you expect end‑users to ask
- Derives a schema and extracts attributes (fields) to support filtered/faceted search
- Creates and indexes documents into Elasticsearch
- Deploys Elasticsearch either locally or remotely (Docker) from the same UI
- Boots a small MCP server next to the remote ES instance so LLMs (or n8n) can query via HTTP endpoints
- Offers health, stats, and MCP visibility endpoints for the UI

## Key files

- `app.py` — Flask application exposing routes:
  - `GET /esportal` — main portal (upload form)
  - `POST /upload` — upload + deploy + index; supports `deployment={local|remote}` and `userQueries`
  - `GET /health` — overall health incl. MCP status
  - `GET /api/stats` — quick stats for UI tiles
  - `GET /mcp/*` — MCP status and test endpoints (`/connections`, `/status`, `/test/:instance_name`)
  - Several helper routes for auth and results; see file for complete list
- `enhanced_data_pipeline.py` — the core pipeline:
  - Parses CSV/JSON files
  - Generates a schema from data
  - Local mode indexing to `CONFIG['es_host']`
  - Remote mode: SSH to VM, run `elasticsearch:8.15.0` in Docker, index data, and spin up MCP server
  - Exposes helpers to list/stop/delete remote instances
- `mcp_integration.py` — assembles a minimal MCP server (aiohttp) on the remote VM next to ES with:
  - `GET /health`, `GET /capabilities`, `GET /index-info`
  - `POST /search`, `POST /prompt`
- `config.py` — environment/configuration knobs for this portal (see below)
- `db_registry.py` — optional: persists a user's ES/MCP endpoints and indices to an external API (`db_api_base`)
- `setup.py` — convenience script to create `requirements.txt`, directories, and a config template

## Configuration (`config.py`)

Edit the following values for your environment before running `app.py`:

- `es_host`: URL to Elasticsearch for local mode (e.g., `http://localhost:9200`)
- `es_auth`: set to `None` for no auth, or `("username", "password")`
- `schema_dir`: directory to write generated schema files (defaults to `schemas/`)
- `db_api_base` (optional): base URL of your external user DB API to persist per-user ES/MCP endpoints and index names

Note: Any credentials present in the repository are placeholders for hackathon demos. Replace with your own values or remove if not applicable. Do not commit real secrets.

## Running locally

1) Install dependencies and prepare config:

```bash
cd frontend
python3 -m venv .venv
source .venv/bin/activate
python setup.py
pip install -r requirements.txt
```

2) Start a local Elasticsearch:

```bash
docker run --rm -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:8.15.0
```

3) Launch the portal:

```bash
python app.py
# Open http://localhost:7000/esportal
```

4) In the portal, upload a CSV/JSON and paste a few example queries. Choose `Local` deployment.

- The pipeline will infer schema and attributes, write `schemas/<index>-schema.json`, create the index in local ES, bulk index documents, and refresh.

## Remote deployment flow

Selecting `Remote` in the upload form:

- SSH to your VM (host/user/password as referenced by the remote managers)
- Stop any prior ES container with the same name
- Run `elasticsearch:8.15.0` on the first available port in 9200..9299
- Index uploaded documents into that ES
- Build and run an MCP server container on `ES_PORT+1000` with endpoints for health, capabilities, index info, search, and prompts
- The portal will surface and optionally auto-open the ES URL and MCP capabilities page

Requirements on the VM:

- Docker installed and running
- SSH access from the machine running the portal
- Open ports 9200..9299 for ES and corresponding MCP ports (ES_PORT + 1000)

Tip: You can “reuse” an existing remote instance if your user profile in the external DB already stores `es_host`/`es_port`.

## Endpoints and contracts (selected)

- `POST /upload`
  - Form fields: `files[]` (CSV/JSON), `deployment` (`local`|`remote`), `userQueries` (multiline string), `description` (optional)
  - Success response includes: index name, counts, schema file path, and either local or remote deployment details (ES URL; MCP URL if available)
- `GET /mcp/status` — returns `mcp_enabled`, active/healthy connection counts, and feature flags
- `GET /mcp/connections` — details of active MCP connections tracked by the remote manager
- `GET /remote-instances` — list remote ES instances with MCP status
- `POST /mcp/test/:instance_name` — quick health test against that MCP server

## Auth and user persistence (optional)

- Descope is used for session auth; you can disable or replace as needed for your environment
- `db_registry.py` integrates with `db_api_base` to persist the latest ES/MCP endpoints and append new index names per user; this enables the “reuse remote” path

## Files generated during runs

- `schemas/<index>-schema.json` — generated mapping + captured queries
- `uploads/` — temporary uploaded files (cleaned up by the flow)

## Troubleshooting

- Upload succeeds but indexing fails in local mode:
  - Ensure your local ES is up and accessible at `es_host`; `curl http://localhost:9200`
- Remote mode fails to start containers:
  - Verify SSH credentials and that the VM user can run Docker (sudo may be used automatically)
  - Check that the ports are open on the VM
- MCP shows unhealthy:
  - Hit `/health` on the MCP URL shown; check ES ping and index name in the MCP logs on the VM

## Security note

This is a hackathon build. Move secrets to environment variables, add auth to ES and MCP in real deployments, and avoid committing credentials.