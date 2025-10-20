# Installation Guide

This guide will walk you through the process of setting up the Generative Indexing service on your system.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.10 or higher
- pip (Python package manager)
- Git

## System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 1GB+ free space
- **OS**: Linux, macOS, or Windows with WSL2

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/abhinav2804/tensile-search-with-strands.git
cd tensile-search-with-strands/generativeIndexing
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "from app.main import app; print('Installation successful!')"
```

## External Dependencies

### AWS Services

1. **AWS Account Setup**
   - Create an AWS account if you don't have one
   - Configure AWS credentials locally
   ```bash
   aws configure
   ```

2. **Required AWS Services**
   - AWS Bedrock access
   - DynamoDB table
   - IAM roles and permissions

### Elasticsearch

1. **Installation Options**
   - Local installation
   - Cloud service (e.g., Elastic Cloud)
   - Docker container

2. **Docker-based Setup**
   ```bash
   docker run -d --name elasticsearch \
     -p 9200:9200 -p 9300:9300 \
     -e "discovery.type=single-node" \
     docker.elastic.co/elasticsearch/elasticsearch:8.10.4
   ```

## Environment Variables

Create a `.env` file in the project root:

```ini
# AWS Configuration
AWS_REGION=your-region
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Elasticsearch Configuration
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-password

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

## Troubleshooting

### Common Issues

1. **Python Version Conflicts**
   ```bash
   python3 --version
   # Ensure version is 3.10 or higher
   ```

2. **Dependency Installation Failures**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt --no-cache-dir
   ```

3. **AWS Credential Issues**
   ```bash
   aws sts get-caller-identity
   # Verify AWS credentials are working
   ```

### Getting Help

- 📝 Check the [troubleshooting guide](../deployment/troubleshooting.md)
- 🐛 [Submit an issue](https://github.com/abhinav2804/tensile-search-with-strands/issues)
- 💬 Join our [community discussions](https://github.com/abhinav2804/tensile-search-with-strands/discussions)

## Next Steps

- ⚙️ [Configure your application](configuration.md)
- 🚀 [Quick start guide](quickstart.md)
- 📚 [Architecture overview](../architecture/overview.md)