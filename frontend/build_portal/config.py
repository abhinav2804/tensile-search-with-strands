CONFIG = {
    'aws_access_key': 'AKIAWRA3N7CH2QNCOCME',
    'aws_secret_key': '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',
    'aws_region': 'us-east-1',
    'es_host': 'http://34.93.165.227:9200',
    'es_auth': None,  # or ('username', 'password')
    'chunk_size': 1000,
    'schema_dir': 'schemas/'
}

# Production Remote Server Configuration
PRODUCTION_SERVER = {
    'host': '82.112.235.26',
    'user': 'root',
    'ssh_key_path': r'C:\Users\Imart\.ssh\id_rsa',  # SSH key authentication
    'password': None,  # Using SSH key instead of password
    'es_base_port': 9200,
    'mcp_base_port': 3000,
    'webhook_url': 'http://82.112.235.26:5678/webhook/search'
}

# Legacy server configuration (kept for reference)
LEGACY_SERVER = {
    'host': '54.227.251.28',
    'user': 'khemchand',
    'password': 'wq0XYdUWKa1EN7LI7'
}

# Default query templates for UI
DEFAULT_QUERY_TEMPLATES = [
    {
        "name": "Search All",
        "query": {"match_all": {}},
        "description": "Retrieve all documents"
    },
    {
        "name": "Full Text Search",
        "query": {"match": {"_all": "{{search_term}}"}},
        "description": "Search across all fields"
    },
    {
        "name": "Exact Match",
        "query": {"term": {"{{field}}": "{{value}}"}},
        "description": "Find exact matches for a specific field"
    },
    {
        "name": "Range Query",
        "query": {"range": {"{{field}}": {"gte": "{{min}}", "lte": "{{max}}"}}},
        "description": "Filter by numeric range"
    },
    {
        "name": "Wildcard Search",
        "query": {"wildcard": {"{{field}}": "*{{pattern}}*"}},
        "description": "Pattern matching with wildcards"
    },
    {
        "name": "Multi-field Search",
        "query": {"multi_match": {"query": "{{search_term}}", "fields": ["{{field1}}", "{{field2}}", "{{field3}}"]}},
        "description": "Search across multiple fields"
    },
    {
        "name": "Boolean Query",
        "query": {"bool": {"must": [{"match": {"{{field}}": "{{value}}"}}], "filter": [{"range": {"{{date_field}}": {"gte": "{{start_date}}"}}}]}},
        "description": "Complex queries with multiple conditions"
    },
    {
        "name": "Aggregation Query",
        "query": {"aggs": {"{{agg_name}}": {"terms": {"field": "{{field}}", "size": 10}}}},
        "description": "Group and count by field values"
    }
]
