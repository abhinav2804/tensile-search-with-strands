# Testing Instructions - Tensile Search with Strands

## Overview
This document provides comprehensive testing procedures for all components of the Tensile Search system. Follow these instructions to validate functionality before hackathon submission or production deployment.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Component Testing](#component-testing)
   - [Upload API Testing](#1-upload-api-testing)
   - [Indexing Agent Testing](#2-indexing-agent-testing)
   - [Search Agent Testing](#3-search-agent-testing)
   - [Frontend Portal Testing](#4-frontend-portal-testing)
   - [Context API Testing](#5-context-api-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Performance Testing](#performance-testing)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
```bash
# Install testing tools
sudo apt-get update
sudo apt-get install -y curl jq httpie

# Python testing tools
pip install pytest requests pytest-asyncio

# Optional: HTTP client with better formatting
sudo apt-get install httpie
```

### Test Data Preparation
```bash
# Navigate to project directory
cd /root/repo/tensile-search-with-strands

# Create test data directory
mkdir -p test-data/{data,query}

# Create sample CSV file
cat > test-data/data/products.csv << 'EOF'
product_id,name,category,price,wattage,brand,color
1,LED Bulb 9W,Lighting,150,9,Syska,Cool White
2,LED Bulb 12W,Lighting,200,12,Philips,Warm White
3,LED Bulb 7W,Lighting,120,7,Havells,Daylight
4,CFL 15W,Lighting,80,15,Bajaj,White
5,LED Tube 18W,Lighting,350,18,Syska,Cool White
EOF

# Create sample query file
cat > test-data/query/search_queries.txt << 'EOF'
Find LED bulbs under 10W
Show me Syska products
Get lighting products between 100-200 rupees
Search for cool white LED bulbs
Find energy efficient bulbs
EOF

# Create sample JSON file
cat > test-data/data/inventory.json << 'EOF'
[
  {
    "sku": "LED-001",
    "name": "Smart LED Bulb",
    "specifications": {
      "wattage": 9,
      "voltage": "220V",
      "lumens": 900
    },
    "stock": 150,
    "location": "Warehouse A"
  },
  {
    "sku": "LED-002",
    "name": "RGB LED Strip",
    "specifications": {
      "wattage": 12,
      "voltage": "12V",
      "length": "5m"
    },
    "stock": 75,
    "location": "Warehouse B"
  }
]
EOF

echo "✅ Test data created successfully!"
```

---

## Component Testing

### 1. Upload API Testing

#### Start Upload API Server
```bash
cd /root/repo/tensile-search-with-strands/api/

# Activate virtual environment (create if doesn't exist)
if [ ! -d "venv_api" ]; then
    python3 -m venv venv_api
    source venv_api/bin/activate
    pip install flask werkzeug
else
    source venv_api/bin/activate
fi

# Start server in background
nohup python app.py > api_test.log 2>&1 &
echo $! > api.pid

# Wait for server to start
sleep 3

# Check server is running
curl http://localhost:5000/health
```

#### Test 1: Health Check
```bash
# Basic health check
curl http://localhost:5000/health

# Expected output:
# {
#   "status": "healthy",
#   "message": "API is running"
# }
```

#### Test 2: Authentication Methods

**Test Basic Auth (Valid)**
```bash
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=test_user_001" \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv"

# Expected: 200 OK with file details
```

**Test Basic Auth (Invalid)**
```bash
curl -X POST http://localhost:5000/upload \
  -u admin:wrongpassword \
  -F "userid=test_user_001" \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv"

# Expected: 401 Unauthorized
```

**Test API Key (Valid)**
```bash
curl -X POST http://localhost:5000/upload \
  -H "X-API-Key: admin123" \
  -H "Authorization: Bearer dummy" \
  -F "userid=test_user_002" \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv"

# Expected: 200 OK
```

**Test Bearer Token (Valid)**
```bash
curl -X POST http://localhost:5000/upload \
  -H "Authorization: Bearer admin123" \
  -F "userid=test_user_003" \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv"

# Expected: 200 OK
```

#### Test 3: File Upload - Data Files
```bash
# Upload CSV file
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv" \
  | jq .

# Upload JSON file
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=data" \
  -F "file=@../test-data/data/inventory.json" \
  | jq .

# Expected output includes:
# - message: "File uploaded successfully"
# - userid: "demo_user"
# - filetype: "data"
# - file_path: "/var/www/es/demo_user/data/..."
```

#### Test 4: File Upload - Query Files
```bash
# Upload query file
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=query" \
  -F "file=@../test-data/query/search_queries.txt" \
  | jq .

# Expected: File saved in /var/www/es/demo_user/query/
```

#### Test 5: List User Files
```bash
# List all files for user
curl -u admin:admin123 http://localhost:5000/list/demo_user | jq .

# Expected output:
# {
#   "userid": "demo_user",
#   "files": [
#     {
#       "filename": "products_abc123.csv",
#       "filetype": "data",
#       "file_path": "/var/www/es/demo_user/data/products_abc123.csv",
#       "file_size": 512,
#       "created_at": 1729612345.67
#     },
#     ...
#   ],
#   "total_files": 3
# }
```

#### Test 6: Error Handling
```bash
# Missing userid
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv"
# Expected: 400 Bad Request - "userid is required"

# Missing filetype
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=test_user" \
  -F "file=@../test-data/data/products.csv"
# Expected: 400 Bad Request - "filetype is required"

# Invalid filetype
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=test_user" \
  -F "filetype=invalid" \
  -F "file=@../test-data/data/products.csv"
# Expected: 400 Bad Request - "filetype must be either 'data' or 'query'"

# Invalid file extension
echo "malicious script" > /tmp/test.exe
curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=test_user" \
  -F "filetype=data" \
  -F "file=@/tmp/test.exe"
# Expected: 400 Bad Request - "File type not allowed"
rm /tmp/test.exe
```

#### Test 7: Directory Structure Validation
```bash
# Verify directory structure was created
ls -la /var/www/es/demo_user/

# Expected structure:
# /var/www/es/demo_user/
# ├── data/
# └── query/

# Verify files are in correct directories
ls -la /var/www/es/demo_user/data/
ls -la /var/www/es/demo_user/query/
```

#### Cleanup Upload API Test
```bash
# Stop API server
if [ -f api.pid ]; then
    kill $(cat api.pid)
    rm api.pid
fi

# Optional: Clean test data
# rm -rf /var/www/es/test_user_* /var/www/es/demo_user
```

---

### 2. Indexing Agent Testing

#### Start Indexing Agent
```bash
cd /root/repo/tensile-search-with-strands/indexing-agent/

# Activate virtual environment
if [ ! -d "venv_indexing" ]; then
    python3 -m venv venv_indexing
    source venv_indexing/bin/activate
    pip install fastapi uvicorn boto3 elasticsearch pandas
else
    source venv_indexing/bin/activate
fi

# Start indexing agent
nohup python app.py > indexing_test.log 2>&1 &
echo $! > indexing.pid

sleep 3
```

#### Test 1: Health Check
```bash
# Check indexing agent homepage
curl http://localhost:8000/ | jq .

# Expected output:
# {
#   "status": "active & kicking 🚀",
#   "uptime": "...",
#   "total_requests": 0,
#   "endpoints": ["/index", "/health", "/status"]
# }
```

#### Test 2: Prerequisites - Elasticsearch
```bash
# Start Elasticsearch (if not running)
docker run -d \
  --name es-test \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.15.0

# Wait for ES to be ready
sleep 30

# Check ES health
curl http://localhost:9200/_cluster/health | jq .

# Expected: status "green" or "yellow"
```

#### Test 3: Prerequisites - DynamoDB Mock (Optional)
```bash
# If testing without real DynamoDB, modify indexing agent to use mock data
# OR ensure DynamoDB table exists with user data

# Mock user data for testing (add to indexing agent code):
# {
#   "userId": "demo_user",
#   "infrastructure": {
#     "elasticsearchHost": "localhost",
#     "elasticsearchPort": 9200
#   }
# }
```

#### Test 4: Trigger Indexing (Streaming Response)
```bash
# Upload test files first (if not already done)
cd /root/repo/tensile-search-with-strands/api/
source venv_api/bin/activate
python app.py &
sleep 3

curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=data" \
  -F "file=@../test-data/data/products.csv"

curl -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=demo_user" \
  -F "filetype=query" \
  -F "file=@../test-data/query/search_queries.txt"

# Now trigger indexing
cd /root/repo/tensile-search-with-strands/indexing-agent/

curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "data_path": "/var/www/es/demo_user/data",
    "query_path": "/var/www/es/demo_user/query"
  }' \
  --no-buffer

# Expected: Streaming response with live updates
# data: Starting indexing process...
# data: Cleaning previous data...
# data: Fetching infrastructure details...
# data: Creating file combinations...
# data: Processing combination 1/2...
# data: ✅ Indexing complete!
```

#### Test 5: Verify Elasticsearch Index Created
```bash
# List all indices
curl http://localhost:9200/_cat/indices?v

# Expected: New index created (e.g., products_lighting_20251022_143022)

# Get index mapping
INDEX_NAME="<index_name_from_above>"
curl http://localhost:9200/${INDEX_NAME}/_mapping | jq .

# Search indexed documents
curl http://localhost:9200/${INDEX_NAME}/_search?pretty | jq .

# Expected: Documents from products.csv indexed
```

#### Test 6: AWS Bedrock Integration (If Available)
```bash
# Ensure AWS credentials are configured
aws configure list

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1 | grep claude-3-5-sonnet

# If credentials are not set, indexing will fail at AI processing stage
```

#### Cleanup Indexing Agent Test
```bash
# Stop indexing agent
if [ -f indexing.pid ]; then
    kill $(cat indexing.pid)
    rm indexing.pid
fi

# Stop test Elasticsearch
docker stop es-test
docker rm es-test
```

---

### 3. Search Agent Testing

#### Prerequisites
```bash
# Ensure Elasticsearch is running with indexed data
docker start es-test || docker run -d \
  --name es-test \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.15.0

sleep 30
```

#### Test 1: Infrastructure Deployment
```bash
cd /root/repo/tensile-search-with-strands/search-agent/

# Start deployment server (if exists)
# python deploy.py &
# sleep 3

# Deploy infrastructure for test user
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "ports": {
      "elasticsearch_port": 7001,
      "mcp_port": 7002,
      "ai_agent_port": 7003
    }
  }' | jq .

# Expected output:
# {
#   "status": "success",
#   "user_id": "usr_abc123",
#   "endpoints": {
#     "elasticsearch": "http://localhost:7001",
#     "mcp": "http://localhost:7002",
#     "search_agent": "http://localhost:7003"
#   }
# }
```

#### Test 2: MCP Server Health
```bash
# Check MCP server is running
curl http://localhost:7002/health

# Test MCP capabilities
curl http://localhost:7002/mcp/capabilities | jq .

# Expected: List of available tools (get_indices, get_mapping, search, etc.)
```

#### Test 3: Search Query Processing
```bash
# Test simple query
curl -X POST http://82.112.235.26:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Get me details of led bulb of 9 watt",
    "temperature": 0.3
  }' | jq .

# Expected output:
# {
#   "query": "Get me details of led bulb of 9 watt",
#   "results": [
#     {
#       "product_id": 1,
#       "name": "LED Bulb 9W",
#       "wattage": 9,
#       "price": 150
#     }
#   ],
#   "total_hits": 1,
#   "explanation": "...",
#   "elasticsearch_query": {...}
# }
```

#### Test 4: Complex Queries
```bash
# Range query
curl -X POST http://82.112.235.26:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me LED bulbs between 7W and 10W under 200 rupees",
    "temperature": 0.3
  }' | jq .

# Brand filter query
curl -X POST http://82.112.235.26:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find all Syska products",
    "temperature": 0.3
  }' | jq .

# Multi-criteria query
curl -X POST http://82.112.235.26:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Get cool white LED bulbs from Syska or Philips under 200",
    "temperature": 0.3
  }' | jq .
```

---

### 4. Frontend Portal Testing

#### Manual Testing Steps

1. **Access Frontend**
   ```bash
   cd /root/repo/tensile-search-with-strands/frontend/
   python -m http.server 8080
   ```
   Open browser: `http://localhost:8080`

2. **Test User Authentication**
   - Click "Login" button
   - Enter email address
   - Verify Descope magic link email received
   - Click magic link and verify redirect to dashboard
   - Check backup login works if Descope fails

3. **Test File Upload**
   - Click "Upload Data" button
   - Fill data description: "Product catalog with LED bulbs"
   - Select file: `test-data/data/products.csv`
   - Click "Upload"
   - Verify progress bar shows upload progress
   - Verify success message appears

4. **Test Query Upload**
   - Click "Upload Queries" button
   - Fill query description: "Search for LED bulbs by wattage and brand"
   - Select file: `test-data/query/search_queries.txt`
   - Click "Upload"
   - Verify file uploaded successfully

5. **Test Search Functionality**
   - Wait for indexing to complete (status shows "Ready")
   - Enter query: "9 watt LED bulb"
   - Click "Search"
   - Verify results displayed in formatted table
   - Check search term highlighting
   - Verify export options (CSV/JSON) work

6. **Test Template Queries**
   - Click on pre-defined template queries
   - Verify they execute and show results
   - Test: Range filter, Fuzzy search, Aggregation queries

#### Automated Frontend Testing (Optional)
```bash
# Install Selenium (if needed)
pip install selenium webdriver-manager

# Create test script
cat > test_frontend.py << 'EOF'
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

try:
    # Test 1: Load homepage
    driver.get("http://localhost:8080")
    assert "Tensile Search" in driver.title
    print("✅ Homepage loaded")
    
    # Test 2: Check login button exists
    login_btn = driver.find_element(By.ID, "login-button")
    assert login_btn is not None
    print("✅ Login button found")
    
    # Test 3: Check upload section exists
    upload_section = driver.find_element(By.ID, "upload-section")
    assert upload_section is not None
    print("✅ Upload section found")
    
    print("\n✅ All frontend tests passed!")
    
finally:
    driver.quit()
EOF

python test_frontend.py
```

---

### 5. Context API Testing

#### Start Context API (Go Service)
```bash
cd /root/repo/tensile-search-with-strands/context-api/

# Build Go application
go build -o context-api main.go

# Run service
./context-api &
echo $! > context-api.pid

sleep 2
```

#### Test 1: Create User
```bash
# Create new user
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test User"
  }' | jq .

# Expected output:
# {
#   "userId": "usr_generated_id",
#   "email": "test@example.com",
#   "name": "Test User",
#   "createdAt": "2025-10-22T14:30:22Z"
# }
```

#### Test 2: Get User
```bash
# Get user by ID
USER_ID="usr_generated_id"
curl http://localhost:8080/users/${USER_ID} | jq .

# Expected: User details returned
```

#### Test 3: Update User Infrastructure
```bash
# Update infrastructure details
curl -X PUT http://localhost:8080/users/${USER_ID}/infrastructure \
  -H "Content-Type: application/json" \
  -d '{
    "elasticsearchPort": 9200,
    "mcpPort": 10200,
    "agentPort": 5000,
    "status": "active"
  }' | jq .

# Expected: Updated user with infrastructure details
```

#### Test 4: List All Users
```bash
# Get all users
curl http://localhost:8080/users | jq .

# Expected: Array of all users
```

#### Cleanup Context API
```bash
if [ -f context-api.pid ]; then
    kill $(cat context-api.pid)
    rm context-api.pid
fi
```

---

## Integration Testing

### Test 1: Complete Upload → Index Flow
```bash
#!/bin/bash
# integration_test_upload_index.sh

echo "Starting Integration Test: Upload → Index"

# 1. Upload data file
echo "Step 1: Uploading data file..."
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=integration_test" \
  -F "filetype=data" \
  -F "file=@test-data/data/products.csv")

echo $UPLOAD_RESPONSE | jq .

# 2. Upload query file
echo "Step 2: Uploading query file..."
curl -s -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=integration_test" \
  -F "filetype=query" \
  -F "file=@test-data/query/search_queries.txt" | jq .

# 3. Trigger indexing
echo "Step 3: Triggering indexing..."
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "integration_test",
    "data_path": "/var/www/es/integration_test/data",
    "query_path": "/var/www/es/integration_test/query"
  }' \
  --no-buffer

# 4. Verify index created
sleep 5
echo -e "\nStep 4: Verifying index creation..."
curl -s http://localhost:9200/_cat/indices?v

echo -e "\n✅ Integration test completed!"
```

### Test 2: Complete Search Flow
```bash
#!/bin/bash
# integration_test_search.sh

echo "Starting Integration Test: Index → Search"

# 1. Create user in DynamoDB (Context API)
echo "Step 1: Creating user..."
USER_RESPONSE=$(curl -s -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "searchtest@example.com",
    "name": "Search Test User"
  }')

USER_ID=$(echo $USER_RESPONSE | jq -r '.userId')
echo "User created: $USER_ID"

# 2. Update infrastructure details
echo "Step 2: Updating infrastructure..."
curl -s -X PUT http://localhost:8080/users/${USER_ID}/infrastructure \
  -H "Content-Type: application/json" \
  -d '{
    "elasticsearchPort": 9200,
    "mcpPort": 10200,
    "agentPort": 5000,
    "status": "active"
  }' | jq .

# 3. Execute search query
echo "Step 3: Executing search..."
curl -s -X POST http://82.112.235.26:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "LED bulb 9 watt",
    "temperature": 0.3
  }' | jq .

echo -e "\n✅ Search integration test completed!"
```

---

## End-to-End Testing

### Complete User Journey Test
```bash
#!/bin/bash
# e2e_test.sh

echo "=========================================="
echo "End-to-End Test: Complete User Journey"
echo "=========================================="

USER_EMAIL="e2e_test@example.com"
USER_ID="e2e_user_$(date +%s)"

# Step 1: User Registration
echo -e "\n[1/6] User Registration..."
curl -s -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$USER_EMAIL\",
    \"name\": \"E2E Test User\"
  }" | jq .

# Step 2: Upload Data File
echo -e "\n[2/6] Uploading data file..."
curl -s -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=$USER_ID" \
  -F "filetype=data" \
  -F "file=@test-data/data/products.csv" | jq .

# Step 3: Upload Query File
echo -e "\n[3/6] Uploading query file..."
curl -s -X POST http://localhost:5000/upload \
  -u admin:admin123 \
  -F "userid=$USER_ID" \
  -F "filetype=query" \
  -F "file=@test-data/query/search_queries.txt" | jq .

# Step 4: Trigger Indexing
echo -e "\n[4/6] Triggering indexing (streaming output)..."
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"data_path\": \"/var/www/es/$USER_ID/data\",
    \"query_path\": \"/var/www/es/$USER_ID/query\"
  }" \
  --no-buffer

# Wait for indexing to complete
sleep 10

# Step 5: Verify Index
echo -e "\n[5/6] Verifying Elasticsearch index..."
curl -s "http://localhost:9200/_cat/indices?v" | grep -i product

# Step 6: Execute Search
echo -e "\n[6/6] Executing search query..."
curl -s -X POST http://82.112.235.26:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "9 watt LED bulb from Syska",
    "temperature": 0.3
  }' | jq .

echo -e "\n=========================================="
echo "✅ End-to-End Test Completed Successfully!"
echo "=========================================="
```

Run the test:
```bash
chmod +x e2e_test.sh
./e2e_test.sh
```

---

## Performance Testing

### Load Testing - Upload API
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test concurrent uploads
ab -n 100 -c 10 -A admin:admin123 \
  -p test-data/data/products.csv \
  -T "multipart/form-data" \
  http://localhost:5000/upload

# Expected metrics:
# - Requests per second: > 50
# - Time per request: < 200ms
# - Failed requests: 0
```

### Load Testing - Search API
```bash
# Create query file for load testing
cat > query_payload.json << 'EOF'
{
  "query": "LED bulb 9 watt",
  "temperature": 0.3
}
EOF

# Test search performance
ab -n 50 -c 5 \
  -p query_payload.json \
  -T "application/json" \
  http://82.112.235.26:5000/query

# Expected metrics:
# - Requests per second: > 10
# - Time per request: < 1000ms
# - Failed requests: 0
```

### Stress Testing - Concurrent Users
```bash
# Install siege
sudo apt-get install siege

# Create URL list
cat > urls.txt << 'EOF'
http://localhost:5000/health
http://localhost:8000/
http://localhost:9200/_cluster/health
EOF

# Run stress test
siege -c 20 -t 30s -f urls.txt

# Metrics to monitor:
# - Availability: > 99%
# - Response time: < 2s
# - Successful transactions: > 95%
```

---

## Troubleshooting

### Issue 1: Upload API Not Starting
```bash
# Check if port 5000 is in use
sudo lsof -i :5000

# Kill existing process
kill -9 $(lsof -t -i:5000)

# Check logs
cat api_test.log

# Verify Python dependencies
pip list | grep -E "flask|werkzeug"
```

### Issue 2: Indexing Agent Fails
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify Elasticsearch connection
curl http://localhost:9200/_cluster/health

# Check indexing agent logs
cat indexing_test.log

# Verify DynamoDB access
aws dynamodb list-tables --region us-east-1
```

### Issue 3: Search Returns No Results
```bash
# Verify index exists
curl http://localhost:9200/_cat/indices?v

# Check document count
INDEX_NAME="your_index_name"
curl "http://localhost:9200/${INDEX_NAME}/_count"

# Inspect indexed documents
curl "http://localhost:9200/${INDEX_NAME}/_search?size=1&pretty"

# Test Elasticsearch query directly
curl -X POST "http://localhost:9200/${INDEX_NAME}/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "name": "LED bulb"
      }
    }
  }'
```

### Issue 4: Frontend Not Loading
```bash
# Check if server is running
ps aux | grep http.server

# Verify file permissions
ls -la frontend/

# Check browser console for JavaScript errors
# Open browser DevTools (F12) and check Console tab

# Test API connectivity from browser console
fetch('http://localhost:5000/health')
  .then(r => r.json())
  .then(console.log)
```

### Issue 5: MCP Server Unreachable
```bash
# Check MCP container status
docker ps | grep mcp

# Check MCP logs
docker logs mcp_container_name

# Verify port mapping
docker port mcp_container_name

# Test MCP endpoint
curl http://localhost:10200/health
```

---

## Test Results Validation

### Success Criteria Checklist

- [ ] **Upload API**
  - [ ] Health check returns 200 OK
  - [ ] Authentication works for all methods (Basic, API Key, Bearer)
  - [ ] Files upload successfully to correct directories
  - [ ] Error handling works for invalid inputs
  - [ ] File listing returns accurate results

- [ ] **Indexing Agent**
  - [ ] Streaming response provides live updates
  - [ ] AWS Bedrock successfully generates schema
  - [ ] Elasticsearch index created with correct mappings
  - [ ] Documents indexed successfully
  - [ ] Summary includes index name and document count

- [ ] **Search Agent**
  - [ ] Infrastructure deployment completes successfully
  - [ ] MCP server responds to health checks
  - [ ] Natural language queries return relevant results
  - [ ] Elasticsearch DSL queries are correctly generated
  - [ ] Results formatted properly

- [ ] **Frontend Portal**
  - [ ] Authentication flow works
  - [ ] File uploads trigger backend API
  - [ ] Search interface displays results
  - [ ] Template queries execute successfully

- [ ] **Integration**
  - [ ] Upload → Index flow completes end-to-end
  - [ ] Index → Search flow returns results
  - [ ] Multi-user isolation works correctly

- [ ] **Performance**
  - [ ] Upload API handles 50+ req/sec
  - [ ] Search responds in < 1 second
  - [ ] System handles 20+ concurrent users

---

## Automated Test Suite (Optional)

### Create Python Test Suite
```bash
# Create pytest test file
cat > test_suite.py << 'EOF'
import pytest
import requests
import time

BASE_URL = "http://localhost:5000"
AUTH = ('admin', 'admin123')

class TestUploadAPI:
    def test_health_check(self):
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'
    
    def test_upload_csv_file(self):
        files = {'file': open('test-data/data/products.csv', 'rb')}
        data = {'userid': 'pytest_user', 'filetype': 'data'}
        
        response = requests.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data,
            auth=AUTH
        )
        
        assert response.status_code == 200
        assert 'file_path' in response.json()
    
    def test_authentication_failure(self):
        files = {'file': open('test-data/data/products.csv', 'rb')}
        data = {'userid': 'test', 'filetype': 'data'}
        
        response = requests.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data,
            auth=('invalid', 'credentials')
        )
        
        assert response.status_code == 401

class TestIndexingAgent:
    def test_indexing_endpoint(self):
        payload = {
            "user_id": "pytest_user",
            "data_path": "/var/www/es/pytest_user/data",
            "query_path": "/var/www/es/pytest_user/query"
        }
        
        response = requests.post(
            "http://localhost:8000/index",
            json=payload,
            stream=True
        )
        
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# Run test suite
pytest test_suite.py -v
```

---

## Conclusion

This testing guide covers:
✅ Individual component testing
✅ Integration testing
✅ End-to-end user journey
✅ Performance and load testing
✅ Troubleshooting common issues

**Before Hackathon Submission**: Run all tests and ensure 100% pass rate.

**For Production Deployment**: Add continuous integration (CI/CD) pipeline with automated testing.

---

**Referenced Documenter**
