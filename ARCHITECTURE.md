# Architecture Deep Dive - Tensile Search with Strands

This document provides an in-depth technical analysis of the Tensile Search system, explaining design decisions, AWS service integration, agent reasoning workflows, and MCP protocol implementation.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [AWS Services Integration](#aws-services-integration)
3. [Agent Architecture](#agent-architecture)
4. [Model Context Protocol (MCP)](#model-context-protocol-mcp)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Decision Trees](#decision-trees)
7. [Scalability & Performance](#scalability--performance)
8. [Security Architecture](#security-architecture)

---

## System Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User Interface Layer                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Frontend Portal (Flask)                             │   │
│  │  - User authentication (Descope)                     │   │
│  │  - File upload interface                             │   │
│  │  - Search query input                                │   │
│  │  - Results visualization                             │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Application Services                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Upload API  │  │ Context API  │  │ Indexing API │       │
│  │  (Flask)    │  │ (Go/DynamoDB)│  │  (FastAPI)   │       │
│  │  Port 5000  │  │  Port 4000   │  │  Port 8000   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                   AI Agent Orchestration                      │
│  ┌────────────────────────┐  ┌────────────────────────┐     │
│  │  Indexing Agent        │  │  Search Agent          │     │
│  │  - Schema generation   │  │  - Query understanding │     │
│  │  - Attribute extraction│  │  - ES query building   │     │
│  │  - Bulk indexing       │  │  - Result formatting   │     │
│  │  AWS Bedrock: Claude   │  │  AWS Bedrock: Claude   │     │
│  └────────────────────────┘  └────────────────────────┘     │
│           │                            │                      │
│           └────────────┬───────────────┘                      │
│                        ▼                                      │
│              ┌──────────────────┐                            │
│              │   MCP Protocol   │                            │
│              │   Tool Layer     │                            │
│              └──────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      AWS Infrastructure                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Bedrock   │  │   DynamoDB   │  │  EC2/Docker  │       │
│  │   Claude    │  │   Registry   │  │  Elasticsearch│       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Flask, Jinja2, Descope | User interface and authentication |
| **API Services** | Flask (Python), Go | Data ingestion and user management |
| **Agent Runtime** | FastAPI, AWS SDK (Boto3) | AI agent execution environment |
| **LLM Reasoning** | AWS Bedrock - Claude 3.5 Sonnet | Autonomous decision-making and schema generation |
| **Agent Framework** | Strands SDK, AWS AgentCore | Multi-agent orchestration and tool calling |
| **Tool Protocol** | Model Context Protocol (MCP) | Standardized LLM-to-tool communication |
| **Search Engine** | Elasticsearch 8.15.0 | Document indexing and retrieval |
| **State Management** | AWS DynamoDB | User metadata and infrastructure registry |
| **Container Orchestration** | Docker, Docker Compose | Per-user infrastructure deployment |

---

## AWS Services Integration

### 1. Amazon Bedrock - Core LLM Reasoning

**Model**: `anthropic.claude-3-5-sonnet-20241022-v2:0`

#### Configuration
```python
# Indexing Agent configuration
bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name='us-east-1',
    aws_access_key_id=CONFIG['aws_access_key'],
    aws_secret_access_key=CONFIG['aws_secret_key']
)

# Model parameters optimized for schema generation
model_config = {
    'modelId': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    'temperature': 0.1,  # Low temperature for deterministic schema design
    'maxTokens': 4000,
    'topP': 0.95,
    'stopSequences': ['</schema>', '</analysis>']
}
```

#### Use Cases

**Indexing Agent - Schema Generation**:
```
Input: 
  - Data sample: First 100 rows of products.csv
  - User queries: ["9W LED bulb", "red color Syska brand"]
  
Bedrock Reasoning:
  1. Analyze data structure (columns, types, patterns)
  2. Identify searchable attributes (brand, wattage, color)
  3. Determine optimal Elasticsearch field types
  4. Generate analyzers for text search (ngram, edge_ngram)
  5. Extract normalization rules (2KW → 2000 in power_watt)
  
Output:
  - Elasticsearch mapping JSON
  - Attribute extraction rules
  - Index settings with analyzers
```

**Search Agent - Query Understanding**:
```
Input:
  - User query: "red or orange LED from Syska or better brands, under 10W"
  - Index schema: {brand: keyword, power_watt: integer, color: keyword}
  
Bedrock Reasoning:
  1. Parse natural language intent
  2. Identify constraints:
     - Color: red OR orange (should clause)
     - Brand: Syska OR "better brands" (Philips, etc.)
     - Wattage: ≤10W (range filter)
  3. Map to Elasticsearch query DSL
  4. Determine bool logic (must, should, filter)
  
Output:
  - Elasticsearch query JSON with proper filters
  - Confidence score for result relevance
```

#### Cost Optimization

- **Batch Processing**: Indexing Agent processes 50 documents per Bedrock call (reduces API calls by 98%)
- **Schema Caching**: Generated schemas stored locally, reused for similar datasets
- **Temperature Control**: 0.1 for indexing (deterministic), 0.3 for search (slight creativity)
- **Token Management**: Max 4000 tokens per call, chunked processing for large datasets

### 2. AWS DynamoDB - User Registry

**Table Schema**:
```json
{
  "TableName": "users",
  "KeySchema": [
    {"AttributeName": "UserId", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "UserId", "AttributeType": "S"}
  ],
  "BillingMode": "PAY_PER_REQUEST",  // Serverless scaling
  "Item": {
    "UserId": "user123",
    "email": "user@example.com",
    "elasticsearch_host": "http://vm-server:9200",
    "elasticsearch_port": 9200,
    "mcp_endpoint": "http://vm-server:10200",
    "indexed_indices": ["products_20251022", "customers_20251023"],
    "created_at": "2025-10-22T10:30:00Z",
    "last_login": "2025-10-22T14:20:00Z"
  }
}
```

**Read/Write Patterns**:
- **Writes**: User creation, infrastructure deployment updates, index additions
- **Reads**: Frontend queries user endpoints, Indexing Agent fetches ES port
- **Consistency**: Eventually consistent reads (acceptable for UI), strongly consistent for critical operations

**Integration Points**:
```go
// Context API (Go) - CRUD operations
GET  /users/{userId}        // Fetch user metadata
POST /users                 // Create new user
PUT  /users/{userId}        // Update infrastructure details
```

### 3. Amazon EC2 + Docker - Elasticsearch Deployment

**Per-User Infrastructure**:

Each user gets a dedicated Elasticsearch instance deployed as a Docker container:

```bash
# Automated deployment by frontend
docker run -d \
  --name es-{userId} \
  -p {dynamic_port}:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx1g" \
  --restart unless-stopped \
  elasticsearch:8.15.0

# Port allocation: 9200-9299 (100 users max per VM)
```

**Resource Management**:
- **Memory**: 1GB JVM heap per instance (configurable)
- **CPU**: Shared across instances, Docker limits available
- **Storage**: Persistent volumes for data retention
- **Networking**: Bridge network with host port mapping

**Health Monitoring**:
```python
def check_elasticsearch_health(host, port):
    """Verify ES cluster health before indexing"""
    try:
        response = requests.get(f"{host}:{port}/_cluster/health")
        health = response.json()
        
        if health['status'] in ['green', 'yellow']:
            return True
        return False
    except:
        return False
```

### 4. Future AWS Services (Roadmap)

#### AWS Lambda - Serverless Indexing
```python
# Convert Indexing Agent to Lambda function
def lambda_handler(event, context):
    """
    Triggered by S3 upload event
    Processes files and indexes to Elasticsearch
    """
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Download file from S3
    s3_client.download_file(bucket, key, '/tmp/data.csv')
    
    # Process with Bedrock
    schema = generate_schema_with_bedrock(file_path)
    
    # Index to Elasticsearch
    bulk_index_documents(schema, documents)
    
    return {'statusCode': 200, 'body': 'Indexing complete'}
```

#### Amazon S3 - Data Lake
- **Large file storage**: Files >100MB uploaded to S3
- **Data versioning**: Track dataset changes over time
- **Cross-region replication**: Global availability

#### Amazon CloudWatch - Monitoring
- **Metrics**: Bedrock API latency, Elasticsearch response times
- **Alarms**: Alert on failed indexing jobs or ES cluster issues
- **Logs**: Centralized logging for all components

---

## Agent Architecture

### Autonomous Agent Qualification

Both agents meet AWS's AI Agent requirements:

#### ✅ Uses Reasoning LLMs for Decision-Making

**Indexing Agent**:
```python
def generate_schema(data_sample, user_queries):
    """
    Claude 3.5 Sonnet autonomously decides:
    1. Which fields should be keyword vs text
    2. Whether to use ngram analyzers for partial matching
    3. How to normalize values (e.g., units conversion)
    4. What additional fields to extract (e.g., price_range from price)
    """
    prompt = f"""
    Analyze this data and generate an Elasticsearch schema:
    
    Data Sample: {data_sample}
    User Query Examples: {user_queries}
    
    Reasoning Requirements:
    - Identify all searchable attributes
    - Determine optimal field types for filtering
    - Extract implicit attributes (e.g., wattage from "6W LED")
    - Design analyzers for fuzzy matching
    - Normalize units (KW → watts, Rs → INR)
    
    Return JSON schema with reasoning explanation.
    """
    
    response = bedrock_client.invoke_model(
        modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
        body=json.dumps({
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.1,  # Deterministic reasoning
            'max_tokens': 4000
        })
    )
    
    return parse_schema_response(response)
```

**Search Agent**:
```python
def build_elasticsearch_query(user_query, index_schema):
    """
    Claude reasons about query intent and constructs ES DSL:
    1. Parse complex boolean logic ("red or orange")
    2. Understand implicit constraints ("better brands" = top brands)
    3. Apply range filters ("under 10W" = lte: 10)
    4. Prioritize exact matches over fuzzy
    """
    prompt = f"""
    Convert this natural language query to Elasticsearch DSL:
    
    User Query: {user_query}
    Available Fields: {index_schema['fields']}
    
    Reasoning Steps:
    1. Identify all constraints (brand, color, price, wattage)
    2. Determine bool clause type (must/should/filter)
    3. Handle synonyms ("LED" = "led bulb", "light")
    4. Apply business logic ("better brands" ranking)
    
    Return: Elasticsearch query JSON
    """
    
    response = bedrock_client.invoke_model(
        modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
        body=json.dumps({
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,  # Slight creativity for synonyms
            'max_tokens': 2000
        })
    )
    
    return parse_query_response(response)
```

#### ✅ Demonstrates Autonomous Capabilities

**Zero Human Intervention**:
1. User uploads `products.csv` and queries
2. System autonomously:
   - Deploys Elasticsearch container
   - Analyzes data structure
   - Generates schema without templates
   - Extracts attributes from text
   - Indexes all documents
   - Deploys MCP server
   - Handles search queries

**Autonomous Decision Examples**:

| Decision Point | Human Input | Agent Reasoning |
|---------------|-------------|-----------------|
| Field type selection | None | "Brand names are keywords (exact match), descriptions are text (analyzed)" |
| Attribute extraction | Product name: "6W Red Syska LED" | Extracts: power_watt=6, color=red, brand=syska, type=led |
| Unit normalization | "2KW", "2000W" | Both become power_watt=2000 for consistent filtering |
| Query understanding | "under 10 wattage" | Translates to: `{"range": {"power_watt": {"lte": 10}}}` |
| Brand ranking | "better brands" | Infers: Syska, Philips, Havells (boosts these in results) |

#### ✅ Integrates External Tools and APIs

**Tool Integration via MCP**:

```python
# Elasticsearch MCP Tools
class ElasticsearchMCPTools:
    """
    Expose Elasticsearch operations as LLM-callable tools
    """
    
    def list_indices(self):
        """Get all indices in the cluster"""
        return es_client.cat.indices(format='json')
    
    def get_mapping(self, index_name):
        """Retrieve field mappings for schema-aware querying"""
        return es_client.indices.get_mapping(index=index_name)
    
    def search(self, index_name, query_dsl):
        """Execute Elasticsearch query"""
        return es_client.search(index=index_name, body=query_dsl)
    
    def bulk_index(self, index_name, documents):
        """Bulk insert documents"""
        actions = [
            {'index': {'_index': index_name, '_id': doc['id']}}
            for doc in documents
        ]
        return es_client.bulk(body=actions)
```

**MCP Server Endpoints**:
```
GET  /health          → Check MCP and ES connectivity
GET  /capabilities    → List available tools
GET  /index-info      → Get schema for query planning
POST /search          → Execute search with LLM-built query
POST /prompt          → Direct LLM invocation with tool access
```

**External APIs Integrated**:
- **AWS Bedrock API**: LLM reasoning and text generation
- **AWS DynamoDB API**: User metadata and state management
- **Elasticsearch API**: Document indexing and search
- **Docker API**: Container orchestration and health checks
- **Descope API**: User authentication (future: AWS Cognito)

#### ✅ Multi-Agent Collaboration

**Agent Handoff Workflow**:

```
1. User uploads data
   ↓
2. Indexing Agent activates
   - Calls Bedrock for schema generation
   - Uses Docker API to deploy Elasticsearch
   - Indexes documents via Elasticsearch API
   - Updates DynamoDB with ES endpoint
   ↓
3. Indexing Agent creates MCP server
   - Configures with ES connection
   - Exposes search tools
   ↓
4. Search Agent activates (on user query)
   - Calls Bedrock for query understanding
   - Uses MCP tools to fetch index schema
   - Builds Elasticsearch query
   - Executes search via MCP
   - Formats results
   ↓
5. Results returned to user
```

**Shared Context**:
- **DynamoDB**: Both agents read user metadata (ES port, indices)
- **MCP Server**: Indexing Agent creates it, Search Agent uses it
- **Elasticsearch**: Indexing Agent writes schema, Search Agent reads it

---

## Model Context Protocol (MCP)

### What is MCP?

Model Context Protocol is a standardized way for LLMs to interact with external tools and data sources. Think of it as an API that LLMs can understand and call autonomously.

### Why MCP vs Direct Elasticsearch API?

| Approach | Challenges | MCP Solution |
|----------|-----------|--------------|
| **Direct ES API** | LLM must know exact API syntax, handle auth, parse responses | MCP provides high-level abstractions |
| **RAG Embedding** | Limited to ~1000 docs, slow updates, hallucinations | MCP queries billions of docs precisely |
| **Hardcoded Queries** | No flexibility, requires code changes | LLM builds queries autonomously |

### MCP Architecture in Tensile Search

```
┌─────────────────────────────────────────────────────┐
│                Search Agent (LLM)                    │
│  "Find red LED bulbs from Syska under 10W"         │
└─────────────────────────────────────────────────────┘
                        │
                        ▼ MCP Tool Call
┌─────────────────────────────────────────────────────┐
│              MCP Server (Port 10200)                 │
│  ┌─────────────────────────────────────────────┐   │
│  │  Tool: get_index_schema()                   │   │
│  │  Returns: {fields: [brand, power_watt, ...]}│   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │  Tool: execute_search(query_dsl)            │   │
│  │  Calls: ES API with authentication          │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│            Elasticsearch (Port 9200)                 │
│  Index: products_user123                            │
│  Query: {"bool": {"must": [...], "filter": [...]}} │
│  Results: 47 matching documents                     │
└─────────────────────────────────────────────────────┘
```

### MCP Implementation

**Server Code** (`mcp_integration.py`):
```python
class ElasticsearchMCPServer:
    """
    Lightweight MCP server exposing Elasticsearch operations
    """
    
    def __init__(self, es_host, es_port, index_name):
        self.es_client = Elasticsearch([f"{es_host}:{es_port}"])
        self.index_name = index_name
    
    @app.get("/health")
    def health_check(self):
        """Verify ES connectivity"""
        try:
            health = self.es_client.cluster.health()
            return {"status": "healthy", "es_status": health['status']}
        except:
            return {"status": "unhealthy"}
    
    @app.get("/capabilities")
    def list_capabilities(self):
        """Advertise available tools to LLM"""
        return {
            "tools": [
                {
                    "name": "get_index_schema",
                    "description": "Retrieve field mappings for query planning",
                    "parameters": {"index_name": "string"}
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
    
    @app.post("/search")
    def execute_search(self, request: SearchRequest):
        """
        Tool callable by LLM via Bedrock AgentCore
        """
        results = self.es_client.search(
            index=self.index_name,
            body=request.query_dsl
        )
        
        # Format for LLM consumption
        return {
            "total_hits": results['hits']['total']['value'],
            "documents": [hit['_source'] for hit in results['hits']['hits']],
            "max_score": results['hits']['max_score']
        }
```

**LLM Tool Calling** (Bedrock side):
```python
# Search Agent invokes MCP tools via Bedrock
def search_with_mcp(user_query):
    """
    LLM autonomously decides which MCP tools to call
    """
    
    # System prompt with tool descriptions
    system_prompt = """
    You are a search agent with access to Elasticsearch via MCP tools.
    
    Available Tools:
    - get_index_schema(index_name): Get field names and types
    - execute_search(index_name, query_dsl): Run ES query
    
    Workflow:
    1. Call get_index_schema to understand available fields
    2. Build Elasticsearch query DSL based on user intent
    3. Call execute_search with constructed query
    4. Format results for user
    """
    
    # Bedrock handles tool orchestration
    response = bedrock_client.converse(
        modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
        messages=[
            {'role': 'user', 'content': user_query}
        ],
        system=system_prompt,
        toolConfig={
            'tools': [
                {
                    'toolSpec': {
                        'name': 'get_index_schema',
                        'description': 'Retrieve ES field mappings',
                        'inputSchema': {
                            'json': {
                                'type': 'object',
                                'properties': {
                                    'index_name': {'type': 'string'}
                                }
                            }
                        }
                    }
                },
                {
                    'toolSpec': {
                        'name': 'execute_search',
                        'description': 'Run ES query',
                        'inputSchema': {
                            'json': {
                                'type': 'object',
                                'properties': {
                                    'index_name': {'type': 'string'},
                                    'query_dsl': {'type': 'object'}
                                }
                            }
                        }
                    }
                }
            ],
            'toolChoice': {'auto': {}}  # LLM decides which tools to call
        }
    )
    
    # Bedrock automatically calls MCP server
    # and returns final results
    return response
```

---

## Data Flow Diagrams

### End-to-End Indexing Flow

```
┌──────────────┐
│ User uploads │ 
│ products.csv │
│ + queries    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Frontend (app.py)                    │
│ 1. Saves files to /var/www/es/      │
│ 2. Calls Upload API                 │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Upload API (Flask)                   │
│ 1. Validates file types              │
│ 2. Creates user directories          │
│ 3. Stores: data/ and query/          │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Frontend triggers deployment         │
│ 1. Calls Context API to create user │
│ 2. Deploys ES container via Docker  │
│ 3. Updates DynamoDB with ES port     │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Indexing Agent (FastAPI)             │
│ GET /triggerIndexingLive             │
│ Query params:                        │
│   - user_id=user123                  │
│   - data_path=/var/www/es/.../data/  │
│   - query_path=/var/www/es/.../query/│
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 1: Fetch User Metadata          │
│ - Call Context API: GET /users/{id}  │
│ - Retrieve: ES host, port, indices   │
│ - Verify ES health                   │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 2: Load Files                   │
│ - Read all CSV/JSON from data_path   │
│ - Read query examples from query_path│
│ - Combine: 1 data file + 1 query file│
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 3: Call AWS Bedrock             │
│ Prompt:                              │
│   Data: [first 100 rows]             │
│   Queries: ["9W LED", "red Syska"]   │
│   Task: Generate ES schema           │
│                                      │
│ Bedrock Response:                    │
│   - Mapping JSON                     │
│   - Field types (keyword, integer)   │
│   - Analyzers (ngram, edge_ngram)    │
│   - Extraction rules                 │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 4: Process Data Rows            │
│ For each row (batch of 50):          │
│   1. Call Bedrock with schema context│
│   2. Extract attributes:             │
│      "6W Red Syska LED" →            │
│        {power_watt: 6, color: red,   │
│         brand: syska}                │
│   3. Normalize values                │
│   4. Append to documents list        │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 5: Create ES Index              │
│ - Generate unique index name:        │
│   products_user123_20251022          │
│ - PUT /{index} with mapping          │
│ - Configure settings (shards, etc.)  │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 6: Bulk Index Documents         │
│ - Batch: 50 docs per bulk request   │
│ - POST /_bulk with all documents     │
│ - Verify: _count matches uploaded    │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 7: Deploy MCP Server            │
│ - Build Docker image with ES config  │
│ - Run on port: ES_PORT + 1000        │
│ - Update DynamoDB with MCP endpoint  │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Step 8: Return Summary               │
│ Response:                            │
│   - Index name                       │
│   - Document count                   │
│   - ES endpoint                      │
│   - MCP endpoint                     │
│   - Processing time                  │
└──────────────────────────────────────┘
```

### Query Processing Flow

```
┌──────────────────┐
│ User enters:     │
│ "red LED under   │
│  10W from Syska" │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Frontend sends query to             │
│ Search Agent API: POST /query       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Search Agent (FastAPI)              │
│ 1. Fetch user's ES endpoint from DB │
│ 2. Prepare Bedrock invocation       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Call AWS Bedrock with MCP tools     │
│ System Prompt: "You have access to  │
│ Elasticsearch via MCP. Build query."│
│                                     │
│ User Message: "red LED under 10W..."│
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Bedrock's Reasoning Process:        │
│ Thought: "I need to know the schema │
│          before building a query"   │
│ Action: Call get_index_schema()     │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ MCP Server: GET /index-info         │
│ Returns: {                          │
│   fields: {                         │
│     brand: {type: keyword},         │
│     power_watt: {type: integer},    │
│     color: {type: keyword}          │
│   }                                 │
│ }                                   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Bedrock continues reasoning:        │
│ Thought: "Schema has color, brand,  │
│   power_watt fields. I can build    │
│   a precise query."                 │
│                                     │
│ Constructs ES Query:                │
│ {                                   │
│   "bool": {                         │
│     "must": [                       │
│       {"term": {"color": "red"}}    │
│     ],                              │
│     "should": [                     │
│       {"term": {"brand": "syska"}}  │
│     ],                              │
│     "filter": [                     │
│       {"range": {                   │
│         "power_watt": {"lte": 10}   │
│       }}                            │
│     ]                               │
│   }                                 │
│ }                                   │
│                                     │
│ Action: Call execute_search()       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ MCP Server: POST /search            │
│ - Receives query DSL               │
│ - Calls Elasticsearch API          │
│ - Returns: 47 matching products    │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Bedrock formats results:            │
│ "Found 47 red LED bulbs under 10W.  │
│  Top match: Syska 9W LED Red, ₹185" │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Search Agent returns to frontend:   │
│ {                                   │
│   "response": "predata,Found 47...",│
│   "status": "success"               │
│ }                                   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Frontend displays results           │
│ - Parses CSV-like format            │
│ - Renders as table/cards            │
│ - Shows metadata (count, filters)   │
└─────────────────────────────────────┘
```

---

## Decision Trees

### Indexing Agent: Field Type Selection

```
For each field in data:
├─ Is it numeric?
│  ├─ YES
│  │  ├─ Contains decimals?
│  │  │  ├─ YES → type: float
│  │  │  └─ NO  → type: integer
│  │  └─ Add range queries to capabilities
│  │
│  └─ NO
│     ├─ Is it a unique identifier?
│     │  ├─ YES → type: keyword (exact match)
│     │  └─ NO → Continue...
│     │
│     ├─ Contains user queries mentioning it?
│     │  ├─ YES
│     │  │  ├─ Query has "search for X"?
│     │  │  │  ├─ YES → type: text + ngram analyzer
│     │  │  │  └─ NO  → type: text + standard analyzer
│     │  │  │
│     │  │  └─ Query has "filter by X"?
│     │  │     ├─ YES → type: keyword + text (multi-field)
│     │  │     └─ NO  → type: text
│     │  │
│     │  └─ NO
│     │     ├─ Is it short (<20 chars average)?
│     │     │  ├─ YES → type: keyword
│     │     │  └─ NO  → type: text
│     │     │
│     │     └─ Has repeated values (>50% duplicate)?
│     │        ├─ YES → type: keyword (faceting)
│     │        └─ NO  → type: text (full-text search)
│     
└─ Special Cases:
   ├─ Field name contains "date", "time", "timestamp"
   │  └─ type: date (with format detection)
   │
   ├─ Field name contains "geo", "location", "coordinates"
   │  └─ type: geo_point or geo_shape
   │
   └─ Field is boolean ("true", "false", "yes", "no")
      └─ type: boolean
```

### Search Agent: Query Construction

```
User Query: "red or orange LED from Syska or better brands, under 10W"

Parse Intent:
├─ Extract Constraints:
│  ├─ Color: ["red", "orange"]           → OR logic
│  ├─ Product: "LED"                     → Must match
│  ├─ Brand: ["Syska", "better brands"]  → OR logic with boost
│  └─ Wattage: "under 10W"              → Range filter
│
├─ Determine Clause Types:
│  ├─ Color: OR logic
│  │  └─ Use: "should" clause (minimum_should_match: 1)
│  │
│  ├─ Product type: Must match
│  │  └─ Use: "must" clause with match query
│  │
│  ├─ Brand: OR with preference
│  │  ├─ Syska → boost: 2.0
│  │  └─ "Better brands" (Philips, Havells) → boost: 1.5
│  │  └─ Use: "should" clause with boosting
│  │
│  └─ Wattage: Hard constraint
│     └─ Use: "filter" clause (doesn't affect score)
│
└─ Build ES Query:
   {
     "query": {
       "bool": {
         "must": [
           {"match": {"type": "led"}}
         ],
         "should": [
           {"term": {"color": {"value": "red"}}},
           {"term": {"color": {"value": "orange"}}},
           {"term": {"brand": {"value": "syska", "boost": 2.0}}},
           {"term": {"brand": {"value": "philips", "boost": 1.5}}},
           {"term": {"brand": {"value": "havells", "boost": 1.5}}}
         ],
         "filter": [
           {"range": {"power_watt": {"lte": 10}}}
         ],
         "minimum_should_match": 1
       }
     },
     "size": 50,
     "sort": [{"_score": "desc"}]
   }
```

---

## Scalability & Performance

### Horizontal Scaling

**Current**: Single VM with 100 users max (ports 9200-9299)

**Future Architecture**:
```
┌─────────────────────────────────────────┐
│ AWS Application Load Balancer           │
│ - Routes users to least-loaded VM       │
│ - Health checks on each VM              │
└────────┬─────────────────────┬──────────┘
         │                     │
    ┌────▼────┐           ┌────▼────┐
    │  VM-1   │           │  VM-2   │
    │ 100 ES  │           │ 100 ES  │
    │instances│           │instances│
    └─────────┘           └─────────┘
    
Total: 200 concurrent users
```

**Lambda Migration** (Serverless):
```
User Upload → S3 Trigger → Lambda (Indexing Agent) → Elasticsearch
User Query  → API Gateway → Lambda (Search Agent) → Bedrock + ES
```

Benefits:
- **No VM management**: AWS handles scaling
- **Pay-per-use**: Only charged for actual processing time
- **Global availability**: Multi-region deployment

### Performance Optimizations

#### 1. Batch Processing
```python
# Before: 1 Bedrock call per document (expensive!)
for doc in documents:
    bedrock_call(doc)  # 1000 docs = 1000 API calls

# After: 1 Bedrock call per 50 documents
for batch in chunk(documents, 50):
    bedrock_call(batch)  # 1000 docs = 20 API calls
    
# Savings: 98% reduction in API calls
```

#### 2. Schema Caching
```python
# Generate schema once, reuse for similar datasets
schema_cache = {}

def get_or_generate_schema(data_fingerprint, data_sample):
    if data_fingerprint in schema_cache:
        return schema_cache[data_fingerprint]
    
    schema = bedrock_generate_schema(data_sample)
    schema_cache[data_fingerprint] = schema
    return schema

# Fingerprint based on column names + data types
fingerprint = hash(f"{columns}_{types}")
```

#### 3. Elasticsearch Bulk API
```python
# Batch: 50-100 documents per bulk request
actions = []
for doc in documents:
    actions.append({'index': {'_index': index_name}})
    actions.append(doc)

# Single bulk request instead of N individual inserts
es_client.bulk(body=actions)
```

#### 4. MCP Connection Pooling
```python
# Reuse HTTP connections to MCP server
session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)

# Reduces connection overhead by 50%
```

### Monitoring & Observability

**Key Metrics**:
- Bedrock API latency (target: <2s per call)
- Elasticsearch indexing rate (target: >1000 docs/sec)
- MCP response time (target: <500ms)
- User query latency (target: <3s end-to-end)

**CloudWatch Alarms**:
```python
# Example alarm: High indexing latency
alarm = cloudwatch.put_metric_alarm(
    AlarmName='IndexingLatencyHigh',
    MetricName='IndexingDuration',
    Threshold=30,  # seconds
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    AlarmActions=['arn:aws:sns:us-east-1:123:alerts']
)
```

---

## Security Architecture

### Authentication Flow

```
User Login
   ↓
┌────────────────┐
│ Descope Auth   │ (OAuth, Email magic link)
│ JWT issued     │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Frontend       │ Store JWT in session
│ Validates JWT  │ on each request
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ API Calls      │ Authorization: Bearer {JWT}
│ (Upload, etc.) │
└────────────────┘
```

### Future: AWS Cognito Integration

```python
# Replace Descope with AWS Cognito
import boto3

cognito_client = boto3.client('cognito-idp')

def authenticate_user(username, password):
    """Authenticate via AWS Cognito User Pool"""
    response = cognito_client.initiate_auth(
        ClientId='your_app_client_id',
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )
    
    return response['AuthenticationResult']['IdToken']
```

### Data Security

**Elasticsearch**:
- Currently: No auth (single-user instances)
- Future: X-Pack security with user-specific credentials

**AWS Bedrock**:
- IAM roles with least-privilege access
- API call logging via CloudTrail

**DynamoDB**:
- Encrypted at rest
- Fine-grained access control per user

### Network Security

```
Internet → AWS WAF → ALB → VPC
                            ├─ Frontend (Public Subnet)
                            ├─ APIs (Private Subnet)
                            └─ Elasticsearch (Private Subnet)
                            
                            DynamoDB (AWS Service, Private)
                            Bedrock (AWS Service, Private)
```

---

## Conclusion

Tensile Search demonstrates a production-ready, autonomous AI agent system leveraging:

✅ **AWS Bedrock** for LLM reasoning (Claude 3.5 Sonnet)  
✅ **AWS AgentCore** for multi-agent orchestration  
✅ **Strands SDK** for tool calling and state management  
✅ **Model Context Protocol** for standardized LLM-tool integration  
✅ **DynamoDB** for serverless state management  
✅ **Docker** for scalable per-user infrastructure  

The architecture balances:
- **Autonomy**: Zero-code deployment, self-generating schemas
- **Precision**: Elasticsearch queries, not hallucinated answers
- **Scalability**: Batch processing, horizontal scaling ready
- **Security**: Multi-layer auth, AWS IAM integration

**Next**: See [SETUP.md](./SETUP.md) for deployment instructions and [README.md](./README.md) for feature overview.

---

**Referenced Documenter**
