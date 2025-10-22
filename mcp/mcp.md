# MCP in this Repository

This repo uses the Model Context Protocol (MCP) to enable LLM‑driven querying of Elasticsearch. There are two cooperating pieces:

1) Elastic MCP Server (reference) — see `tools/mcp-server-elasticsearch/` for the upstream server with rich capabilities and Dockerfiles.

2) Lightweight MCP server (remote sidecar) — created automatically by the `frontend` pipeline when you deploy to a remote VM. It runs next to your Elasticsearch container and exposes a small HTTP surface for prompts and searches.

## Endpoints (lightweight MCP server)

The sidecar MCP server exposes the following endpoints (aiohttp):

- `GET /health` — returns health and the bound Elasticsearch URL/index
- `GET /capabilities` — describes available operations and example usage
- `GET /index-info` — returns index stats and mapping
- `POST /search` — body: `{ "query": "...", "size": 10 }`
- `POST /prompt` — body: `{ "prompt": "..." }`, a simplified prompt→query path

URLs are printed in the portal logs and surfaced in API responses when you deploy in Remote mode. By convention the MCP port is `ES_PORT + 1000`.

## How it plugs into the flow

1. You upload a CSV/JSON and choose Remote deployment in the portal.
2. The pipeline spins up Elasticsearch in Docker on the VM, indexes your documents, then builds and starts the MCP server container.
3. The portal reports the ES URL and the MCP base URL; you can paste the MCP base URL into the Search Agent (n8n) config.

## Using the reference Elastic MCP server

If you prefer the upstream server, check `tools/mcp-server-elasticsearch/` for its README and Dockerfiles, then point the Search Agent to that MCP base URL. Both variants speak simple HTTP with `/health`, and support a JSON search request body the agent can craft.

## Security and hardening (post‑hackathon)

- Add authentication to both ES and MCP endpoints
- Move VM credentials and keys to environment variables or secret stores
- Restrict exposed ports with firewall rules and use TLS if public

