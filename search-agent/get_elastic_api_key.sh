#!/bin/bash

# Script to get Elasticsearch API key after services are running
echo "Getting Elasticsearch API key..."

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s -u elastic:changeme http://localhost:9200/_cluster/health > /dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 5
done

echo "Elasticsearch is ready. Creating API key..."

# Create API key
response=$(curl -s -u elastic:changeme -X POST 'http://localhost:9200/_security/api_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "aws-strand-agent",
    "expiration": "30d",
    "role_descriptors": {
      "my_custom_role": {
        "cluster": ["all"],
        "index": [{
          "names": ["*"],
          "privileges": ["read", "write"]
        }]
      }
    }
  }')

echo "API Key Response:"
echo "$response"

# Extract the encoded API key
api_key=$(echo "$response" | grep -o '"encoded":"[^"]*"' | cut -d'"' -f4)

if [ -n "$api_key" ]; then
    echo ""
    echo "==================================="
    echo "Generated API Key: $api_key"
    echo "==================================="
    echo ""
    echo "Add this to your .env file:"
    echo "ES_API_KEY=$api_key"
    echo "ES_URL=http://localhost:9200"
else
    echo "Failed to extract API key from response"
    exit 1
fi