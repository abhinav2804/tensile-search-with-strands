# Demo Walkthrough

This guide shows how to run an end‑to‑end demo of the zero‑code search stack using the portal, remote deployment, and the search agent.

## 1) Prepare the environment

- Follow the root `README.md` Quick Start to run the portal locally.
- Decide whether you’ll demo Local or Remote deployment:
	- Local: run an ES container on your laptop (port 9200)
	- Remote: ensure your VM is reachable via SSH and has Docker installed

## 2) Upload data and example queries

1. Open `http://localhost:7000/esportal`
2. Upload a CSV/JSON file (see `frontend/data/` for samples)
3. Paste 3–5 example user queries, e.g.:
	 - “Want to buy red or orange LED from Syska or better brands, under 10 wattage.”
	 - “9W LED, exclude blue, prefer Syska”
4. Choose `Local` to keep it on your machine, or `Remote` to spin up ES + MCP on the VM

After submission, the portal prints the new index name, document counts, and (for remote) links to ES and MCP.

## 3) Inspect the index (optional)

- Use Kibana (or `curl`) to view the mapping and a few documents
- Check the generated schema in `frontend/schemas/<index>-schema.json`

## 4) Use the Search Agent (n8n)

1. Import `search-agent/N8N -  Search Agent.json` into n8n
2. Set your model/API key and the Elastic MCP base URL
3. Trigger the workflow with your prompt; observe responses

## 5) Screenshots

See `demo/screenshots/` for portal upload, MCP capabilities, and sample responses.

## Tips for a crisp demo

- Keep your dataset modest (a few thousand rows) to keep indexing snappy
- Use clear example queries that reflect attributes present in your data (brand, wattage, color, etc.)
- If remote, pre-warm the VM and open ports so Docker pulls and health checks complete quickly

