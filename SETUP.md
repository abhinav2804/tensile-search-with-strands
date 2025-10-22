# Setup Instructions - Tensile Search with Strands

This document provides **precise, step-by-step instructions** for deploying the Tensile Search system. All paths, ports, and configurations reflect the **actual deployed architecture**.

---

## 🌐 Production Deployment

### Live Portal Access

**Primary Interface**: [https://search.lehana.in/build](https://search.lehana.in/build)

This is the main entry point for users to interact with the system. The portal is already deployed and running.

### System Architecture Overview

The deployed system consists of multiple services:

```
Production Architecture:
┌─────────────────────────────────────────────────────┐
│ Frontend Portal                                     │
│ Location: /root/repo/tensile-search-with-strands/  │
│ URL: https://search.lehana.in/build                │
│ Components:                                         │
│  - Flask UI (app.py)                               │
│  - Indexing Agent Pipeline                         │
│  - MCP Integration Layer                           │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Backend Services                                    │
│                                                     │
│ 1. Upload API                                       │
│    Location: /root/repo/tensile-search-with-strands/api/
│    Port: 5000                                       │
│    Purpose: File upload management                 │
│                                                     │
│ 2. Context API (DynamoDB)                          │
│    Location: /root/repo/tensile-search-with-strands/context-api/
│    Port: 4000                                       │
│    Purpose: User metadata storage                  │
│                                                     │
│ 3. Indexing Agent                                  │
│    Location: /root/repo/tensile-search-with-strands/indexing-agent/
│    Port: 8000                                       │
│    Purpose: AI-powered schema generation           │
│                                                     │
│ 4. Search Agent                                    │
│    Location: /root/repo/tensile-search-with-strands/search-agent/
│    Port: Variable (5000+)                          │
│    Purpose: Natural language query processing      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Per-User Infrastructure (Dynamically Deployed)     │
│                                                     │
│ For each user, the system deploys:                 │
│  - Elasticsearch Container (Port: 9200-9299)       │
│  - MCP Server (Port: 10200-11299)                  │
│  - Search Agent Instance                           │
│                                                     │
│ Deployment: Docker containers on EC2/VM            │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Component Setup

### 1. Frontend Portal Setup

**Location**: `/root/repo/tensile-search-with-strands/frontend/`

#### Prerequisites
- Python 3.10+
- AWS credentials with Bedrock access
- Elasticsearch instance (local or remote)

#### Installation Steps

```bash
# Navigate to frontend directory
cd /root/repo/tensile-search-with-strands/frontend/

# Create virtual environment (if not exists)
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
.\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

#### Configuration

Edit `config.py` with your environment settings:

```python
CONFIG = {
    # AWS Credentials
    'aws_access_key': 'YOUR_AWS_ACCESS_KEY',
    'aws_secret_key': 'YOUR_AWS_SECRET_KEY',
    'aws_region': 'us-east-1',
    
    # Elasticsearch Configuration
    'es_host': 'http://localhost:9200',  # For local ES
    # OR
    'es_host': 'https://your-es-endpoint.com',  # For remote ES
    'es_auth': None,  # For no auth
    # OR
    'es_auth': ('username', 'password'),  # For basic auth
    
    # External API endpoints
    'db_api_base': 'http://localhost:4000',  # DynamoDB API
    
    # Descope Authentication (optional)
    'descope_project_id': 'YOUR_PROJECT_ID',
}
```

#### Running the Portal

```bash
# Start Flask server
python app.py

# Portal will be available at:
# http://localhost:7000/esportal
```

#### What This Component Does

1. **Accepts file uploads** (CSV, JSON, XML, TXT)
2. **Processes user queries** (example search queries for context)
3. **Triggers the Indexing Agent** to generate schema
4. **Deploys infrastructure** (Elasticsearch + MCP) for each user
5. **Provides search interface** to query the deployed system

---

### 2. Upload API Setup

**Location**: `/root/repo/tensile-search-with-strands/api/`

#### Installation

```bash
cd /root/repo/tensile-search-with-strands/api/

# Create virtual environment
python3 -m venv venv_api
source venv_api/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configuration

Edit `config.py`:

```python
# File storage location
BASE_DIR = "/var/www/es"  # User data storage path

# Authentication
API_KEYS = {
    'admin': 'admin123',
    'user1': 'user1pass',
}
```

#### Running the API

```bash
python app.py

# API will be available at:
# http://localhost:5000
```

#### API Endpoints

```bash
# Health check
curl http://localhost:5000/health

# Upload file (data or query)
curl -X POST http://localhost:5000/upload \
  -H "Authorization: Basic $(echo -n 'admin:admin123' | base64)" \
  -F "userid=user123" \
  -F "filetype=data" \
  -F "file=@dataset.csv"

# List user files
curl -H "Authorization: Basic $(echo -n 'admin:admin123' | base64)" \
  http://localhost:5000/list/user123
```

#### What This Component Does

1. **Receives file uploads** from frontend
2. **Stores files** in `/var/www/es/{userid}/data/` or `/var/www/es/{userid}/query/`
3. **Provides file listing** for user management
4. **Handles authentication** via multiple methods (Basic, Bearer, API Key)

---

### 3. Context API (DynamoDB) Setup

**Location**: `/root/repo/tensile-search-with-strands/context-api/`

#### Prerequisites
- Go 1.18+ installed
- AWS credentials configured
- DynamoDB table created

#### Installation

```bash
cd /root/repo/tensile-search-with-strands/context-api/

# Install dependencies
go mod download

# Build binary
go build -o main main.go dynamo.go
```

#### AWS Configuration

```bash
# Configure AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# OR use AWS CLI
aws configure
```

#### DynamoDB Table Setup

```bash
# Create table (if not exists)
aws dynamodb create-table \
    --table-name users \
    --attribute-definitions \
        AttributeName=UserId,AttributeType=S \
    --key-schema \
        AttributeName=UserId,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
```

#### Running the API

```bash
./main

# API will be available at:
# http://localhost:4000
```

#### API Endpoints

```bash
# Create user
curl -X POST http://localhost:4000/users \
  -H "Content-Type: application/json" \
  -d '{
    "UserId": "user123",
    "email": "user@example.com",
    "elasticsearch_port": 9200,
    "mcp_port": 10200
  }'

# Get user details
curl http://localhost:4000/users/user123

# Update user
curl -X PUT http://localhost:4000/users/user123 \
  -H "Content-Type: application/json" \
  -d '{
    "elasticsearch_port": 9201,
    "indexed_indices": ["products", "customers"]
  }'
```

#### What This Component Does

1. **Stores user metadata** in DynamoDB
2. **Tracks deployed infrastructure** (ES ports, MCP endpoints)
3. **Manages indexed indices** per user
4. **Provides CRUD operations** for user registry

---

### 4. Indexing Agent Setup

**Location**: `/root/repo/tensile-search-with-strands/indexing-agent/`

#### Installation

```bash
cd /root/repo/tensile-search-with-strands/indexing-agent/

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configuration

Edit `app/config/config.yaml`:

```yaml
aws:
  region: us-east-1
  bedrock_model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
  dynamodb:
    table_name: users

elasticsearch:
  host: localhost
  port: 9200
  username: elastic  # Optional
  password: your_password  # Optional
  default_index: my_index

app:
  host: 0.0.0.0
  port: 8000
  chunk_size: 1000
  docs_per_batch: 50
```

#### Running the Service

```bash
# Production
python app/main.py

# Development (with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### API Usage

```bash
# Trigger indexing with streaming updates
curl -N "http://localhost:8000/triggerIndexingLive?user_id=user123&data_path=/var/www/es/user123/data/&user_query_path=/var/www/es/user123/query/"

# Response is streamed JSON events:
# {"stage": "dynamo_fetch", "status": "success", "data": {...}}
# {"stage": "file_processing", "status": "in_progress", ...}
# {"stage": "bedrock_enhancement", "status": "success", ...}
# {"stage": "elasticsearch_indexing", "status": "complete", ...}
```

#### What This Component Does

1. **Fetches user metadata** from DynamoDB (ES port, configuration)
2. **Reads uploaded files** from `/var/www/es/{userid}/`
3. **Calls AWS Bedrock** (Claude 3.5 Sonnet) to:
   - Analyze data structure
   - Generate Elasticsearch schema
   - Extract attributes from rows
4. **Creates Elasticsearch index** with optimized mappings
5. **Bulk indexes documents** with batch processing
6. **Streams progress updates** via Server-Sent Events

---

### 5. Search Agent Setup

**Location**: `/root/repo/tensile-search-with-strands/search-agent/`

#### Installation

```bash
cd /root/repo/tensile-search-with-strands/search-agent/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configuration

Edit `elastic_mapping_tool.py` for Elasticsearch connection:

```python
# Elasticsearch configuration
elastic_endpoint = "https://your-elasticsearch-endpoint"
elastic_api_key = "your_api_key"
# OR use basic auth
# elastic_username = "elastic"
# elastic_password = "your_password"
```

Edit `api_wrapper.py` for AWS Bedrock:

```python
bedrock_model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name="us-east-1",
    temperature=0.3,
)
```

#### Running the Service

```bash
python start_api.py

# API will be available at:
# http://localhost:5000
```

#### API Usage

```bash
# Health check
curl http://localhost:5000/health

# Query with natural language
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Get me LED bulbs of 9 watt in red or orange color from Syska",
    "temperature": 0.3
  }'

# Async query (recommended)
curl -X POST http://localhost:5000/query-async \
  -H "Content-Type: application/json" \
  -d '{
    "query": "List all indices",
    "temperature": 0.3
  }'
```

#### What This Component Does

1. **Receives natural language queries** from users
2. **Calls AWS Bedrock** (Claude 3.5 Sonnet) to understand intent
3. **Uses Elasticsearch MCP** to:
   - List available indices
   - Get index mappings
   - Build precise Elasticsearch queries
4. **Returns structured results** in CSV-like format
5. **Handles complex filters** (range, boolean, brand preferences)

---

## 🐳 Docker Deployment (Per-User Infrastructure)

### Elasticsearch Container

When a user uploads data, the system automatically deploys an Elasticsearch container:

```bash
# Example deployment command (automated by frontend)
docker run -d \
  --name es-user123 \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.15.0
```

**Port allocation**: `9200-9299` (first available port)

### MCP Server Container

Each user also gets an MCP server for tool integration:

```bash
# Example MCP deployment (automated)
docker run -d \
  --name mcp-user123 \
  -p 10200:8080 \
  -e ES_HOST=http://localhost:9200 \
  -e ES_INDEX=products_user123 \
  mcp-elasticsearch-server
```

**Port allocation**: `10200-11299` (ES_PORT + 1000)

### Health Checks

```bash
# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check MCP server
curl http://localhost:10200/health
```

---

## 🔄 Complete Workflow

### User Journey from Portal to Results

#### Step 1: User Uploads Data

1. User visits `https://search.lehana.in/build`
2. Logs in via Descope (or fallback authentication)
3. Uploads dataset file (e.g., `products.csv`)
4. Uploads query examples (e.g., "9W LED bulbs under ₹200")

**Backend Flow**:
```
Frontend (app.py) 
  → Upload API (port 5000) 
  → Stores files in /var/www/es/{userid}/
```

#### Step 2: Infrastructure Deployment

Frontend triggers deployment:

```python
# In enhanced_data_pipeline.py
remote_es_manager.deploy_elasticsearch(userid)
mcp_integration.setup_mcp_server(es_port, index_name)
```

**Backend Flow**:
```
Frontend
  → Docker API
  → Creates ES container (port 9200-9299)
  → Creates MCP container (port 10200-11299)
  → Updates DynamoDB with ports
```

#### Step 3: Schema Generation & Indexing

Indexing Agent processes the data:

```
Frontend
  → POST /triggerIndexingLive (port 8000)
  → Indexing Agent reads files
  → Calls AWS Bedrock for schema
  → Creates ES index with mapping
  → Bulk indexes documents
  → Returns summary
```

**What Gets Created**:
- Elasticsearch index: `products_user123_20251022`
- Schema file: `/frontend/schemas/products_user123_20251022-schema.json`
- Document count: e.g., 1,247 products
- Fields extracted: `brand`, `power_watt`, `color`, `price_inr`, etc.

#### Step 4: User Queries

User enters natural language query in portal:

```
Query: "Want red or orange LED from Syska or better brands, under 10 wattage"
```

**Backend Flow**:
```
Frontend
  → POST /query (Search Agent, port 5000)
  → Search Agent calls AWS Bedrock
  → Bedrock uses Elasticsearch MCP
  → MCP executes query on ES
  → Results returned to frontend
```

**Elasticsearch Query Built** (automatic):
```json
{
  "query": {
    "bool": {
      "must": [
        {"range": {"power_watt": {"lte": 10}}}
      ],
      "should": [
        {"term": {"color": "red"}},
        {"term": {"color": "orange"}},
        {"term": {"brand": "syska"}},
        {"term": {"brand": "philips"}}  // "better brands" reasoning
      ],
      "minimum_should_match": 1
    }
  }
}
```

#### Step 5: Results Display

Frontend receives structured response:

```
predata: Found 47 matching LED products
header: [Product Name, Brand, Wattage, Color, Price]
data: [
  {Syska 9W LED Bulb Red, Syska, 9, red, ₹185},
  {Philips 6W LED Orange, Philips, 6, orange, ₹199}
]
postdata: All results match criteria: ≤10W, red/orange, preferred brands
finaly: Would you like to filter by price range or see specifications?
```

---

## 🔐 Environment Variables

Create a `.env` file in each component directory:

### Frontend `.env`
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
DESCOPE_PROJECT_ID=your_project_id
ES_HOST=http://localhost:9200
DB_API_BASE=http://localhost:4000
```

### Indexing Agent `.env`
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Search Agent `.env`
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
ES_ENDPOINT=https://your-es-endpoint
ES_API_KEY=your_api_key
```

---

## 🧪 Testing the Setup

### Test 1: Upload API
```bash
curl http://localhost:5000/health
# Expected: {"status": "healthy", "message": "API is running"}
```

### Test 2: DynamoDB API
```bash
curl -X POST http://localhost:4000/users \
  -d '{"UserId": "test123", "email": "test@example.com"}'
# Expected: {"UserId": "test123", "email": "test@example.com"}
```

### Test 3: Indexing Agent
```bash
# Ensure test files exist at /var/www/es/test123/
curl -N "http://localhost:8000/triggerIndexingLive?user_id=test123&data_path=/var/www/es/test123/data/&user_query_path=/var/www/es/test123/query/"
# Expected: Streaming JSON events with progress
```

### Test 4: Search Agent
```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List all indices", "temperature": 0.3}'
# Expected: Structured response with index list
```

### Test 5: End-to-End Portal
1. Open `http://localhost:7000/esportal`
2. Upload `data/sample-products.csv`
3. Paste query: "9W LED bulbs"
4. Click "Deploy"
5. Wait for indexing complete
6. Enter query: "red LED under 10 watt"
7. View results

---

## 🐛 Troubleshooting

### Issue: Indexing Agent Can't Connect to AWS Bedrock

**Symptom**: `boto3.exceptions.NoCredentialsError`

**Solution**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1

# Ensure model ID is correct
anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Issue: Elasticsearch Connection Failed

**Symptom**: `ConnectionError: Connection refused`

**Solution**:
```bash
# Check if ES is running
docker ps | grep elasticsearch

# Check ES health
curl http://localhost:9200/_cluster/health

# Restart ES if needed
docker restart es-user123
```

### Issue: MCP Server Unhealthy

**Symptom**: `/health` returns 503

**Solution**:
```bash
# Check MCP logs
docker logs mcp-user123

# Verify ES connection from MCP
docker exec mcp-user123 curl http://host.docker.internal:9200

# Restart MCP
docker restart mcp-user123
```

### Issue: Search Agent Returns Empty Results

**Symptom**: Query completes but no data returned

**Solution**:
1. Verify index exists: `curl http://localhost:9200/_cat/indices`
2. Check document count: `curl http://localhost:9200/your_index/_count`
3. Test direct ES query: `curl -X POST http://localhost:9200/your_index/_search -d '{"query": {"match_all": {}}}'`
4. Check Search Agent logs for query construction errors

---

## 📊 Port Allocation Reference

| Service | Port Range | Purpose |
|---------|-----------|---------|
| Frontend Portal | 7000 | Main UI |
| Upload API | 5000 | File management |
| Context API | 4000 | DynamoDB access |
| Indexing Agent | 8000 | Schema generation |
| Search Agent | 5000+ | Query processing |
| Elasticsearch (per-user) | 9200-9299 | Document storage |
| MCP Server (per-user) | 10200-11299 | Tool integration |

---

## 📚 Configuration Files Reference

- **Frontend**: `/root/repo/tensile-search-with-strands/frontend/config.py`
- **Upload API**: `/root/repo/tensile-search-with-strands/api/config.py`
- **Context API**: `/root/repo/tensile-search-with-strands/context-api/main.go` (table name)
- **Indexing Agent**: `/root/repo/tensile-search-with-strands/indexing-agent/app/config/config.yaml`
- **Search Agent**: `/root/repo/tensile-search-with-strands/search-agent/api_wrapper.py` + `elastic_mapping_tool.py`

---

## 🎯 Next Steps

After setup is complete:

1. **Test with sample data**: Use datasets in `/data/` directory
2. **Review generated schemas**: Check `/frontend/schemas/` for auto-generated mappings
3. **Monitor AWS Bedrock usage**: Check CloudWatch for API calls and costs
4. **Scale infrastructure**: Add more EC2 instances for multi-user deployments
5. **Customize prompts**: Edit system prompts in `elasticsearch_agent_prompt.py` for domain-specific improvements

---

## 📞 Support

For setup issues:
1. Check component logs in respective directories
2. Verify AWS credentials and permissions
3. Ensure all ports are available and not blocked by firewall
4. Review DynamoDB table structure and data

---

**Referenced Documenter**
