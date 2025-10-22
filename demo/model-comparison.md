# Model Comparison Guide

This guide outlines how to compare different LLM configurations driving the Search Agent (n8n) against the same Elasticsearch/MCP backend.

## Purpose

Demonstrate how attribute‑aware search quality and response latency vary across models and settings when querying the same index produced by the portal.

## Setup

1. Use the portal to create a single index from your dataset (Local or Remote).
2. Ensure the MCP server `/health` is healthy for that index.
3. Import `search-agent/N8N -  Search Agent.json` into n8n.
4. Duplicate the workflow once per model you want to test (e.g., Claude, GPT‑4o, etc.).
5. In each copy, set the model/API credentials and keep the same MCP base URL.

## Prompts to test (examples)

- “Want to buy red or orange LED from Syska or better brands, under 10 wattage.”
- “Exclude blue, 9W preferred, show top 10.”
- “LED bulbs compatible with E27 base, warm white, under 400 lumens.”

Keep prompts identical across workflows.

## Metrics to record

- Precision@K — proportion of top‑K results that match intent/filters
- Attribute correctness — did brand/wattage/color constraints hold?
- Query latency — time from webhook trigger to final answer
- Readability — clarity/conciseness of the final response

## How to measure

1. Trigger each workflow with the same prompt.
2. Capture:
	- MCP `/search` request body and response time
	- Final LLM output and total time
3. Validate top results against ground truth (if available) or manual criteria.

## Recording results

- Place screenshots in `demo/screenshots/`.
- Summarize findings in a table (model, settings, P@K, attr correctness, latency, notes).

## Notes

- If responses look empty, verify your index fields and mapping; try a simpler prompt.
- For consistency, keep ES/MCP endpoints identical across runs and only change the model settings.

