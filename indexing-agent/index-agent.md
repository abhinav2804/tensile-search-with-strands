# Index Agent — Attribute Extraction + Schema Generation

The Index Agent is embodied by the enhanced data pipeline in `frontend/`. It transforms raw files into an Elasticsearch index configured for fast, attribute‑aware search.

## Responsibilities

- Parse CSV/JSON into normalized documents
- Derive a schema (mapping) from data, with text + keyword subfields
- Extract attributes to support faceted/filtered queries based on your example prompts
- Bulk index into ES and refresh
- Orchestrate deployment target: `local` (existing ES) or `remote` (spin up ES + MCP)

## Flow overview

1. Upload: You provide one or more files plus a few example user queries in the portal.
2. Parse: The pipeline loads CSV/JSON records and normalizes values.
3. Schema: A mapping is generated with best‑effort field types and keyword subfields.
4. Attributes: Fields appropriate for filtering are highlighted; these power UI facets / agent filters.
5. Index:
	- Local mode — index to `CONFIG['es_host']`
	- Remote mode — SSH to VM → run Docker ES → index → start MCP sidecar
6. Persist (optional): If user persistence is configured, the ES/MCP endpoints and new index name are stored for your user profile for later reuse.

## Artifacts

- `schemas/<index>-schema.json` — generated mapping and captured auto‑queries
- Index in ES named like `upload-<user>-<basename>-<timestamp>`

## Managing remote instances

The portal exposes:

- `GET /remote-instances` — list remote ES instances (with MCP status where available)
- `POST /remote-instances/:name/stop` — stop an ES container (and its MCP)
- `DELETE /remote-instances/:name/delete` — remove the ES container (and its MCP and build context)

## Notes

- The attribute extraction leverages your provided example queries to bias the schema towards fields that matter for filtering (e.g., brand, wattage, color).
- For speed during the demo, analyzers are kept simple and types conservative; you can refine mapping rules post‑hackathon for your data domain(s).

