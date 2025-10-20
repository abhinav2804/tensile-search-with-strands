# Configuration Guide

This guide explains how to configure the Generative Indexing service for your specific needs.

## Configuration Files

The service uses two main configuration methods:
1. YAML configuration file (`app/config/config.yaml`)
2. Environment variables

## YAML Configuration

### Basic Structure

```yaml
aws:
  region: us-west-2
  bedrock_model_id: anthropic.claude-v2
  dynamodb:
    table_name: user-metadata
    endpoint: http://localhost:8000  # Optional, for local testing

elasticsearch:
  host: localhost
  port: 9200
  username: elastic
  password: your-password
  default_index: documents
  settings:
    number_of_shards: 1
    number_of_replicas: 1
  mappings:
    properties:
      content:
        type: text
        analyzer: standard
      metadata:
        type: object
        enabled: true

app:
  host: 0.0.0.0
  port: 8000
  chunk_size: 1000
  docs_per_batch: 50
  queries_per_batch: 10
  log_level: INFO
```

### Configuration Sections

#### AWS Configuration

```yaml
aws:
  region: us-west-2  # AWS region for services
  bedrock_model_id: anthropic.claude-v2  # Bedrock model identifier
  dynamodb:
    table_name: user-metadata  # DynamoDB table name
    endpoint: http://localhost:8000  # Optional local endpoint
```

#### Elasticsearch Configuration

```yaml
elasticsearch:
  host: localhost  # Elasticsearch host
  port: 9200  # Elasticsearch port
  username: elastic  # Authentication username
  password: your-password  # Authentication password
  default_index: documents  # Default index name
  settings:  # Index settings
    number_of_shards: 1
    number_of_replicas: 1
  mappings:  # Index mappings
    properties:
      content:
        type: text
        analyzer: standard
      metadata:
        type: object
        enabled: true
```

#### Application Configuration

```yaml
app:
  host: 0.0.0.0  # Application host
  port: 8000  # Application port
  chunk_size: 1000  # Document chunk size
  docs_per_batch: 50  # Documents per batch for processing
  queries_per_batch: 10  # Queries per batch for processing
  log_level: INFO  # Logging level
```

## Environment Variables

Environment variables override YAML configurations. Create a `.env` file in the project root:

```ini
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_BEDROCK_MODEL_ID=anthropic.claude-v2
AWS_DYNAMODB_TABLE=user-metadata

# Elasticsearch Configuration
ES_HOST=localhost
ES_PORT=9200
ES_USERNAME=elastic
ES_PASSWORD=your-password
ES_DEFAULT_INDEX=documents

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=INFO
APP_CHUNK_SIZE=1000
APP_DOCS_PER_BATCH=50
```

## Advanced Configuration

### Logging Configuration

Customize logging in `app/utils/logger.py`:

```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "default"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO"
    }
}
```

### Schema Configuration

Customize document schema in `app/processors/schema_processor.py`:

```python
DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        }
    },
    "required": ["content"]
}
```

## Security Best Practices

1. **Environment Variables**
   - Never commit `.env` files
   - Use secret management services in production

2. **AWS Credentials**
   - Use IAM roles when possible
   - Implement least privilege principle
   - Rotate credentials regularly

3. **Elasticsearch Security**
   - Enable TLS/SSL
   - Use strong passwords
   - Implement IP whitelisting

## Configuration Validation

The service validates configurations on startup. Example validation code:

```python
def validate_config():
    """Validate required configuration settings."""
    required_settings = [
        "AWS_REGION",
        "AWS_BEDROCK_MODEL_ID",
        "ES_HOST",
        "ES_PORT"
    ]
    
    missing = [setting for setting in required_settings 
              if not os.getenv(setting)]
    
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")
```

## Next Steps

- 🚀 [Quick Start Guide](quickstart.md)
- 🏗️ [Architecture Overview](../architecture/overview.md)
- 📚 [API Documentation](../api/endpoints.md)