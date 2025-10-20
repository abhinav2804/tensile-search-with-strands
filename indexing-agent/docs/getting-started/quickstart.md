# Quick Start Guide

Get up and running with Generative Indexing in minutes! This guide will walk you through a basic setup and your first document indexing pipeline.

## Prerequisites

Ensure you have:
- ✅ Completed the [installation](installation.md)
- ✅ Set up your [configuration](configuration.md)
- ✅ Access to AWS services
- ✅ Running Elasticsearch instance

## 5-Minute Quick Start

### 1. Start the Service

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the service
python app/main.py
```

You should see:
```
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Prepare Sample Data

Create a sample JSON file `sample.json`:

```json
{
  "documents": [
    {
      "title": "Sample Document",
      "content": "This is a test document for indexing.",
      "metadata": {
        "tags": ["test", "sample"],
        "timestamp": "2025-10-20T12:00:00Z"
      }
    }
  ]
}
```

### 3. Trigger Indexing

```bash
curl -N "http://localhost:8000/triggerIndexingLive?user_id=test-user&data_path=/path/to/sample.json"
```

You'll receive real-time updates:
```json
{"status": "started", "message": "Starting indexing pipeline"}
{"status": "processing", "message": "Reading input file"}
{"status": "processing", "message": "Processing with AWS Bedrock"}
{"status": "processing", "message": "Indexing to Elasticsearch"}
{"status": "completed", "message": "Indexing completed successfully"}
```

## Basic Operations

### Check Service Health

```bash
curl http://localhost:8000/health
```

### View API Documentation

Open in your browser:
```
http://localhost:8000/docs
```

### Monitor Processing Status

```bash
curl http://localhost:8000/status?job_id=<job_id>
```

## Working with Different File Formats

### CSV Files

```csv
title,content,tags
Document 1,Content for doc 1,"tag1,tag2"
Document 2,Content for doc 2,"tag2,tag3"
```

```bash
curl -N "http://localhost:8000/triggerIndexingLive?user_id=test-user&data_path=/path/to/documents.csv"
```

### JSONL Files

```jsonl
{"title": "Doc 1", "content": "Content 1", "tags": ["tag1"]}
{"title": "Doc 2", "content": "Content 2", "tags": ["tag2"]}
```

```bash
curl -N "http://localhost:8000/triggerIndexingLive?user_id=test-user&data_path=/path/to/documents.jsonl"
```

## Processing Pipeline

1. **File Reading**
   - Automatic format detection
   - Chunked processing for large files

2. **AWS Bedrock Processing**
   - Content enhancement
   - Metadata extraction
   - Error handling

3. **Elasticsearch Indexing**
   - Bulk operations
   - Progress tracking
   - Error recovery

## Code Examples

### Python Client

```python
import requests
import json
import sseclient

def index_documents(user_id, data_path):
    url = f"http://localhost:8000/triggerIndexingLive"
    params = {
        "user_id": user_id,
        "data_path": data_path
    }
    
    response = requests.get(url, params=params, stream=True)
    client = sseclient.SSEClient(response)
    
    for event in client.events():
        print(json.loads(event.data))

# Usage
index_documents("test-user", "/path/to/documents.json")
```

### Async Processing

```python
from app.services.indexing_pipeline import IndexingPipeline
import asyncio

async def process_documents(data_path):
    pipeline = IndexingPipeline()
    async for status in pipeline.process(data_path):
        print(status)

# Usage
asyncio.run(process_documents("/path/to/documents.json"))
```

## Common Issues and Solutions

### Connection Issues

```bash
# Check Elasticsearch
curl localhost:9200/_cat/health

# Check AWS credentials
aws sts get-caller-identity
```

### Processing Errors

- Verify file format matches content
- Check document schema compliance
- Ensure sufficient permissions

## Next Steps

- 📚 Learn about the [Architecture](../architecture/overview.md)
- 🔌 Explore the [API Reference](../api/endpoints.md)
- 🔧 Read about [Advanced Configuration](../deployment/advanced-config.md)
- 🚀 Check out [Deployment Options](../deployment/prerequisites.md)