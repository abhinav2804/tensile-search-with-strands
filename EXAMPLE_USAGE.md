# API Example Usage - Tensile Search

This document provides practical examples for testing and using the Tensile Search APIs.

---

## 🌐 Live Demo

**Primary Interface**: https://search.lehana.in/build

For API testing, use the following endpoints:

---

## 1. Upload API (Port 5000)

### Health Check
```bash
curl http://localhost:5000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "message": "API is running"
}
```

### Upload Data File

```bash
# Using Basic Authentication
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=user123" \
  -F "filetype=data" \
  -F "file=@products.csv"
```

**Expected Response**:
```json
{
  "message": "File uploaded successfully",
  "userid": "user123",
  "filetype": "data",
  "filename": "products_a3f8c2e1.csv",
  "file_path": "/var/www/es/user123/data/products_a3f8c2e1.csv",
  "file_size": 524288
}
```

### Upload Query File

```bash
# Using API Key Authentication
curl -X POST http://localhost:5000/upload \
  -H "X-API-Key: admin123" \
  -F "userid=user123" \
  -F "filetype=query" \
  -F "file=@search_examples.txt"
```

### List User Files

```bash
# Using Bearer Token
curl -H "Authorization: Bearer admin123" \
  http://localhost:5000/list/user123
```

**Expected Response**:
```json
{
  "userid": "user123",
  "files": [
    {
      "filename": "products_a3f8c2e1.csv",
      "filetype": "data",
      "file_path": "/var/www/es/user123/data/products_a3f8c2e1.csv",
      "file_size": 524288,
      "created_at": 1729607400.123
    },
    {
      "filename": "search_examples_b5e3f9c2.txt",
      "filetype": "query",
      "file_path": "/var/www/es/user123/query/search_examples_b5e3f9c2.txt",
      "file_size": 2048,
      "created_at": 1729607450.456
    }
  ],
  "total_files": 2
}
```

---

## 2. Context API - DynamoDB (Port 4000)

### Create User

```bash
curl -X POST http://localhost:4000/users \
  -H "Content-Type: application/json" \
  -d '{
    "UserId": "user123",
    "email": "user@example.com",
    "elasticsearch_port": 9200,
    "mcp_port": 10200
  }'
```

**Expected Response**:
```json
{
  "UserId": "user123",
  "email": "user@example.com",
  "elasticsearch_port": 9200,
  "mcp_port": 10200
}
```

### Get User Details

```bash
curl http://localhost:4000/users/user123
```

**Expected Response**:
```json
{
  "UserId": "user123",
  "email": "user@example.com",
  "elasticsearch_host": "http://localhost:9200",
  "elasticsearch_port": 9200,
  "mcp_endpoint": "http://localhost:10200",
  "indexed_indices": ["products_20251022"],
  "created_at": "2025-10-22T10:30:00Z"
}
```

### Update User Infrastructure

```bash
curl -X PUT http://localhost:4000/users/user123 \
  -H "Content-Type: application/json" \
  -d '{
    "elasticsearch_port": 9201,
    "indexed_indices": ["products_20251022", "customers_20251023"]
  }'
```

**Expected Response**:
```json
{
  "message": "User updated successfully"
}
```

---

## 3. Indexing Agent (Port 8000)

### Trigger Indexing with Streaming Updates

```bash
# -N flag enables streaming (Server-Sent Events)
curl -N "http://localhost:8000/triggerIndexingLive?user_id=user123&data_path=/var/www/es/user123/data/&user_query_path=/var/www/es/user123/query/"
```

**Expected Streaming Response**:
```json
{"stage": "init", "status": "started", "message": "Indexing pipeline initialized"}

{"stage": "dynamo_fetch", "status": "in_progress", "message": "Fetching user metadata from DynamoDB"}
{"stage": "dynamo_fetch", "status": "success", "data": {"elasticsearch_port": 9200, "user_id": "user123"}}

{"stage": "file_processing", "status": "in_progress", "message": "Loading data files"}
{"stage": "file_processing", "status": "success", "data": {"files_found": 2, "total_rows": 1247}}

{"stage": "bedrock_enhancement", "status": "in_progress", "message": "Calling AWS Bedrock for schema generation"}
{"stage": "bedrock_enhancement", "status": "success", "data": {"schema_generated": true, "fields_extracted": 12}}

{"stage": "bedrock_enhancement", "status": "in_progress", "message": "Processing batch 1 of 25"}
{"stage": "bedrock_enhancement", "status": "success", "data": {"batch": 1, "documents_processed": 50}}

{"stage": "elasticsearch_indexing", "status": "in_progress", "message": "Creating Elasticsearch index"}
{"stage": "elasticsearch_indexing", "status": "success", "data": {"index_name": "products_user123_20251022"}}

{"stage": "elasticsearch_indexing", "status": "in_progress", "message": "Bulk indexing documents"}
{"stage": "elasticsearch_indexing", "status": "success", "data": {"documents_indexed": 1247}}

{"stage": "complete", "status": "success", "summary": {
  "index_name": "products_user123_20251022",
  "document_count": 1247,
  "processing_time_seconds": 45.6,
  "elasticsearch_endpoint": "http://localhost:9200",
  "mcp_endpoint": "http://localhost:10200"
}}
```

### Alternative: Non-Streaming (Wait for Completion)

```bash
# Without -N flag, waits for full completion
curl "http://localhost:8000/triggerIndexingLive?user_id=user123&data_path=/var/www/es/user123/data/&user_query_path=/var/www/es/user123/query/"
```

---

## 4. Search Agent (Port 5000)

### Health Check

```bash
curl http://localhost:5000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "message": "Search Agent operational",
  "elasticsearch_connected": true,
  "bedrock_available": true
}
```

### Natural Language Search Query

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Get me LED bulbs of 9 watt in red or orange color from Syska",
    "temperature": 0.3
  }'
```

**Expected Response**:
```json
{
  "response": "predata,Found 47 matching LED products\nheader,[Product Name, Brand, Wattage, Color, Price]\ndata,[{Syska 9W LED Bulb Red, Syska, 9, red, ₹185}, {Syska 7W LED Orange, Syska, 7, orange, ₹165}]\npostdata,All results match your criteria: 7-9W range, red/orange colors, Syska brand\nfinaly,Would you like to see additional specifications or filter by price range?",
  "status": "success",
  "metadata": {
    "total_hits": 47,
    "query_time_ms": 234,
    "confidence_score": 0.95
  }
}
```

### Async Search (Recommended for Production)

```bash
curl -X POST http://localhost:5000/query-async \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Want red or orange LED from Syska or better brands, under 10 wattage",
    "temperature": 0.3
  }'
```

### List Available Search Tools

```bash
curl http://localhost:5000/tools
```

**Expected Response**:
```json
{
  "tools": [
    {
      "name": "list_indices",
      "description": "Get all Elasticsearch indices",
      "parameters": {}
    },
    {
      "name": "get_mapping",
      "description": "Retrieve field mappings for an index",
      "parameters": {
        "index_name": "string"
      }
    },
    {
      "name": "execute_search",
      "description": "Run Elasticsearch query",
      "parameters": {
        "index_name": "string",
        "query_dsl": "object"
      }
    }
  ]
}
```

### Example: List All Indices

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "List all indices",
    "temperature": 0.3
  }'
```

### Example: Get Index Mapping

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Get mapping for products_user123_20251022 index",
    "temperature": 0.3
  }'
```

---

## 5. Elasticsearch Direct Access (Port 9200)

### Check Cluster Health

```bash
curl http://localhost:9200/_cluster/health?pretty
```

**Expected Response**:
```json
{
  "cluster_name" : "docker-cluster",
  "status" : "yellow",
  "timed_out" : false,
  "number_of_nodes" : 1,
  "number_of_data_nodes" : 1,
  "active_primary_shards" : 3,
  "active_shards" : 3
}
```

### List All Indices

```bash
curl http://localhost:9200/_cat/indices?v
```

**Expected Response**:
```
health status index                      pri rep docs.count docs.deleted store.size
yellow open   products_user123_20251022    1   1       1247            0      2.3mb
```

### Get Index Mapping

```bash
curl http://localhost:9200/products_user123_20251022/_mapping?pretty
```

**Expected Response**:
```json
{
  "products_user123_20251022" : {
    "mappings" : {
      "properties" : {
        "brand" : {
          "type" : "keyword"
        },
        "color" : {
          "type" : "keyword"
        },
        "power_watt" : {
          "type" : "integer"
        },
        "price_inr" : {
          "type" : "float"
        },
        "product_name" : {
          "type" : "text",
          "analyzer" : "standard"
        }
      }
    }
  }
}
```

### Count Documents

```bash
curl http://localhost:9200/products_user123_20251022/_count?pretty
```

**Expected Response**:
```json
{
  "count" : 1247,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  }
}
```

### Direct Search Query

```bash
curl -X POST http://localhost:9200/products_user123_20251022/_search?pretty \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"color": "red"}}
        ],
        "filter": [
          {"range": {"power_watt": {"lte": 10}}}
        ]
      }
    },
    "size": 10
  }'
```

---

## 6. MCP Server (Port 10200)

### Health Check

```bash
curl http://localhost:10200/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "elasticsearch_status": "green",
  "index_name": "products_user123_20251022",
  "document_count": 1247
}
```

### Get MCP Capabilities

```bash
curl http://localhost:10200/capabilities
```

**Expected Response**:
```json
{
  "tools": [
    {
      "name": "get_index_schema",
      "description": "Retrieve field mappings for query planning",
      "parameters": {
        "index_name": "string"
      }
    },
    {
      "name": "execute_search",
      "description": "Run Elasticsearch query and return results",
      "parameters": {
        "index_name": "string",
        "query_dsl": "object"
      }
    }
  ]
}
```

### Get Index Information

```bash
curl http://localhost:10200/index-info
```

**Expected Response**:
```json
{
  "index_name": "products_user123_20251022",
  "fields": {
    "brand": {"type": "keyword"},
    "color": {"type": "keyword"},
    "power_watt": {"type": "integer"},
    "price_inr": {"type": "float"},
    "product_name": {"type": "text"}
  },
  "document_count": 1247,
  "size": "2.3mb"
}
```

### Execute Search via MCP

```bash
curl -X POST http://localhost:10200/search \
  -H "Content-Type: application/json" \
  -d '{
    "index_name": "products_user123_20251022",
    "query_dsl": {
      "query": {
        "bool": {
          "must": [
            {"term": {"brand": "syska"}}
          ],
          "filter": [
            {"range": {"power_watt": {"lte": 10}}}
          ]
        }
      }
    }
  }'
```

**Expected Response**:
```json
{
  "total_hits": 47,
  "documents": [
    {
      "product_name": "Syska 9W LED Bulb Red",
      "brand": "syska",
      "power_watt": 9,
      "color": "red",
      "price_inr": 185.0
    }
  ],
  "max_score": 1.0
}
```

---

## 7. End-to-End Workflow Example

### Step 1: Create User

```bash
curl -X POST http://localhost:4000/users \
  -H "Content-Type: application/json" \
  -d '{
    "UserId": "demo_user",
    "email": "demo@example.com"
  }'
```

### Step 2: Upload Data File

```bash
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=data" \
  -F "file=@sample_products.csv"
```

### Step 3: Upload Query Examples

```bash
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=query" \
  -F "file=@search_queries.txt"
```

### Step 4: Trigger Indexing

```bash
curl -N "http://localhost:8000/triggerIndexingLive?user_id=demo_user&data_path=/var/www/es/demo_user/data/&user_query_path=/var/www/es/demo_user/query/"
```

### Step 5: Wait for Completion (Watch Streaming Output)

The indexing agent will stream progress updates. Wait for the final `"stage": "complete"` message.

### Step 6: Verify Index Created

```bash
curl http://localhost:9200/_cat/indices?v | grep demo_user
```

### Step 7: Test Search

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find red LED bulbs under 10 watts from Syska",
    "temperature": 0.3
  }'
```

---

## 8. Troubleshooting Commands

### Check All Service Health

```bash
# Upload API
curl http://localhost:5000/health

# Context API (DynamoDB)
curl http://localhost:4000/users/test_user 2>&1 | grep -q "404" && echo "User not found (normal)" || echo "Service OK"

# Indexing Agent
curl http://localhost:8000/docs

# Search Agent
curl http://localhost:5000/health

# Elasticsearch
curl http://localhost:9200/_cluster/health

# MCP Server
curl http://localhost:10200/health
```

### View Elasticsearch Logs

```bash
# If running in Docker
docker logs es-demo_user

# If running locally
tail -f /var/log/elasticsearch/elasticsearch.log
```

### Clear Test Data

```bash
# Delete test user files
rm -rf /var/www/es/demo_user/

# Delete Elasticsearch index
curl -X DELETE http://localhost:9200/products_demo_user_*

# Remove user from DynamoDB (via Context API)
# (Update API needed - PUT with empty fields)
```

---

## 9. Sample Data Files

### products.csv
```csv
product_name,brand,power_watt,color,price_inr
"Syska 9W LED Bulb Red",syska,9,red,185
"Philips 6W LED Orange",philips,6,orange,199
"Havells 7W LED White",havells,7,white,175
"Syska 6W LED Blue",syska,6,blue,165
```

### search_queries.txt
```
9W LED bulbs
red or orange color LED
Syska brand products
LED under 10 watts
warm white LED bulbs under 200 rupees
```

---

## 10. Python Client Example

```python
import requests
import json

# Configuration
UPLOAD_API = "http://localhost:5000"
CONTEXT_API = "http://localhost:4000"
INDEXING_API = "http://localhost:8000"
SEARCH_API = "http://localhost:5000"

# Authentication
AUTH = ("admin", "admin123")

def create_user(user_id, email):
    """Create user in DynamoDB"""
    response = requests.post(
        f"{CONTEXT_API}/users",
        json={"UserId": user_id, "email": email}
    )
    return response.json()

def upload_file(user_id, file_path, file_type):
    """Upload data or query file"""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'userid': user_id, 'filetype': file_type}
        response = requests.post(
            f"{UPLOAD_API}/upload",
            auth=AUTH,
            data=data,
            files=files
        )
    return response.json()

def trigger_indexing(user_id):
    """Start indexing process"""
    response = requests.get(
        f"{INDEXING_API}/triggerIndexingLive",
        params={
            'user_id': user_id,
            'data_path': f'/var/www/es/{user_id}/data/',
            'user_query_path': f'/var/www/es/{user_id}/query/'
        },
        stream=True
    )
    
    # Print streaming updates
    for line in response.iter_lines():
        if line:
            event = json.loads(line)
            print(f"Stage: {event.get('stage')}, Status: {event.get('status')}")
    
    return "Indexing complete"

def search(query):
    """Execute natural language search"""
    response = requests.post(
        f"{SEARCH_API}/query",
        json={"query": query, "temperature": 0.3}
    )
    return response.json()

# Example usage
if __name__ == "__main__":
    user_id = "python_client_user"
    
    # Step 1: Create user
    print("Creating user...")
    user = create_user(user_id, "python@example.com")
    print(f"User created: {user}")
    
    # Step 2: Upload files
    print("Uploading data file...")
    upload_result = upload_file(user_id, "products.csv", "data")
    print(f"Upload result: {upload_result}")
    
    print("Uploading query file...")
    upload_result = upload_file(user_id, "queries.txt", "query")
    print(f"Upload result: {upload_result}")
    
    # Step 3: Trigger indexing
    print("Starting indexing...")
    trigger_indexing(user_id)
    
    # Step 4: Search
    print("Executing search...")
    results = search("Find red LED bulbs from Syska under 10 watts")
    print(f"Search results: {results}")
```

---

## 📚 Related Documentation

- [Main README](./README.md) - Project overview
- [SETUP.md](./SETUP.md) - Deployment instructions
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design
- [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md) - Complete documentation index

---

**Referenced Documenter**
