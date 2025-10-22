import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import yaml
import os
import subprocess
import tempfile
from elasticsearch import Elasticsearch
import docker
import threading
import time

logger = logging.getLogger(__name__)

class MCPElasticsearchServer:
    """
    MCP Server that automatically connects to Elasticsearch instances
    and manages the docker-compose configuration for seamless integration
    """
    
    def __init__(self, base_port=9200):
        self.base_port = base_port
        self.active_connections = {}
        self.docker_client = None
        self.mcp_configs = {}
        self.compose_files = {}
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
    
    def generate_docker_compose_config(self, instance_name: str, port: int, 
                                     es_host: str, es_password: str = None) -> Dict[str, Any]:
        """
        Generate docker-compose configuration for MCP server connection
        """
        config = {
            'version': '3.8',
            'services': {
                f'mcp-{instance_name}': {
                    'image': 'mcp-elasticsearch:latest',
                    'container_name': f'mcp-{instance_name}',
                    'environment': {
                        'ELASTICSEARCH_URL': f'http://{es_host}:{port}',
                        'ELASTICSEARCH_INDEX': instance_name,
                        'MCP_SERVER_NAME': f'elasticsearch-{instance_name}',
                        'LOG_LEVEL': 'INFO'
                    },
                    'ports': [
                        f'{port + 1000}:8080'  # MCP server port
                    ],
                    'depends_on': [instance_name] if es_host == 'localhost' else [],
                    'networks': ['elasticsearch-network'],
                    'restart': 'unless-stopped',
                    'healthcheck': {
                        'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                        'interval': '30s',
                        'timeout': '10s',
                        'retries': 3
                    }
                }
            },
            'networks': {
                'elasticsearch-network': {
                    'external': True
                }
            }
        }
        
        # Add Elasticsearch service if local deployment
        if es_host == 'localhost':
            config['services'][instance_name] = {
                'image': 'elasticsearch:8.15.0',
                'container_name': instance_name,
                'environment': {
                    'discovery.type': 'single-node',
                    'xpack.security.enabled': 'false',
                    'ES_JAVA_OPTS': '-Xms512m -Xmx512m'
                },
                'ports': [f'{port}:9200'],
                'networks': ['elasticsearch-network'],
                'volumes': [
                    f'{instance_name}-data:/usr/share/elasticsearch/data'
                ]
            }
            
            config['volumes'] = {
                f'{instance_name}-data': {
                    'driver': 'local'
                }
            }
        
        return config
    
    def create_mcp_server_dockerfile(self) -> str:
        """
        Create Dockerfile for MCP Elasticsearch server
        """
        dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY mcp_server.py .
COPY config.py .

# Expose MCP server port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run MCP server
CMD ["python", "mcp_server.py"]
"""
        return dockerfile_content
    
    def create_mcp_server_code(self) -> str:
        """
        Create the actual MCP server Python code
        """
        server_code = '''
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from elasticsearch import Elasticsearch
from aiohttp import web
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPElasticsearchHandler:
    def __init__(self):
        self.es_url = os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.index_name = os.environ.get('ELASTICSEARCH_INDEX', 'default')
        self.server_name = os.environ.get('MCP_SERVER_NAME', 'elasticsearch-mcp')
        
        # Initialize Elasticsearch client
        self.es = Elasticsearch([self.es_url], verify_certs=False, request_timeout=30)
        
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            if self.es.ping():
                return web.json_response({
                    'status': 'healthy',
                    'elasticsearch_url': self.es_url,
                    'index': self.index_name,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return web.json_response({
                    'status': 'unhealthy',
                    'error': 'Cannot connect to Elasticsearch'
                }, status=503)
        except Exception as e:
            return web.json_response({
                'status': 'unhealthy',
                'error': str(e)
            }, status=503)
    
    async def search_documents(self, request):
        """Search documents in Elasticsearch"""
        try:
            data = await request.json()
            query = data.get('query', '*')
            size = data.get('size', 10)
            
            search_body = {
                'query': {
                    'query_string': {
                        'query': query
                    }
                },
                'size': min(size, 100)
            }
            
            result = self.es.search(index=self.index_name, body=search_body)
            
            return web.json_response({
                'total_hits': result['hits']['total']['value'],
                'documents': [hit['_source'] for hit in result['hits']['hits']],
                'took': result['took']
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_index_info(self, request):
        """Get index information"""
        try:
            # Get index stats
            stats = self.es.indices.stats(index=self.index_name)
            mapping = self.es.indices.get_mapping(index=self.index_name)
            
            return web.json_response({
                'index': self.index_name,
                'document_count': stats['indices'][self.index_name]['total']['docs']['count'],
                'store_size': stats['indices'][self.index_name]['total']['store']['size_in_bytes'],
                'mapping': mapping[self.index_name]['mappings'],
                'server_name': self.server_name
            })
            
        except Exception as e:
            logger.error(f"Index info error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def mcp_capabilities(self, request):
        """MCP protocol capabilities endpoint"""
        return web.json_response({
            'capabilities': {
                'search': True,
                'index_info': True,
                'real_time': False
            },
            'server_info': {
                'name': self.server_name,
                'version': '1.0.0',
                'elasticsearch_url': self.es_url,
                'index': self.index_name
            }
        })

async def create_app():
    handler = MCPElasticsearchHandler()
    app = web.Application()
    
    # Add routes
    app.router.add_get('/health', handler.health_check)
    app.router.add_post('/search', handler.search_documents)
    app.router.add_get('/index-info', handler.get_index_info)
    app.router.add_get('/capabilities', handler.mcp_capabilities)
    
    return app

if __name__ == '__main__':
    app = asyncio.run(create_app())
    web.run_app(app, host='0.0.0.0', port=8080)
'''
        return server_code
    
    def create_requirements_txt(self) -> str:
        """Create requirements.txt for MCP server"""
        return """
elasticsearch>=8.0.0
aiohttp>=3.8.0
asyncio
"""
    
    async def setup_mcp_connection(self, instance_name: str, es_host: str, 
                                 es_port: int, deployment_type: str = 'local') -> Dict[str, Any]:
        """
        Setup MCP server connection for a new Elasticsearch instance
        """
        try:
            logger.info(f"Setting up MCP connection for {instance_name}")
            
            # Create directory for this instance
            mcp_dir = f"mcp_configs/{instance_name}"
            os.makedirs(mcp_dir, exist_ok=True)
            
            # Generate docker-compose config
            compose_config = self.generate_docker_compose_config(
                instance_name, es_port, es_host
            )
            
            # Write docker-compose file
            compose_file_path = os.path.join(mcp_dir, 'docker-compose.yml')
            with open(compose_file_path, 'w') as f:
                yaml.dump(compose_config, f, default_flow_style=False)
            
            # Create MCP server files
            dockerfile_path = os.path.join(mcp_dir, 'Dockerfile')
            with open(dockerfile_path, 'w') as f:
                f.write(self.create_mcp_server_dockerfile())
            
            server_code_path = os.path.join(mcp_dir, 'mcp_server.py')
            with open(server_code_path, 'w') as f:
                f.write(self.create_mcp_server_code())
            
            requirements_path = os.path.join(mcp_dir, 'requirements.txt')
            with open(requirements_path, 'w') as f:
                f.write(self.create_requirements_txt())
            
            # Build MCP Docker image
            build_result = await self.build_mcp_image(mcp_dir, instance_name)
            if not build_result['success']:
                return build_result
            
            # Start MCP server
            start_result = await self.start_mcp_server(mcp_dir, instance_name)
            
            if start_result['success']:
                # Store connection info
                mcp_port = es_port + 1000
                self.active_connections[instance_name] = {
                    'es_host': es_host,
                    'es_port': es_port,
                    'mcp_port': mcp_port,
                    'mcp_url': f'http://{es_host}:{mcp_port}',
                    'compose_file': compose_file_path,
                    'deployment_type': deployment_type,
                    'created_at': datetime.now().isoformat()
                }
                
                logger.info(f"MCP server started successfully for {instance_name}")
                
                return {
                    'success': True,
                    'instance_name': instance_name,
                    'mcp_url': f'http://{es_host}:{mcp_port}',
                    'es_url': f'http://{es_host}:{es_port}',
                    'compose_file': compose_file_path,
                    'capabilities': [
                        'document_search',
                        'index_information',
                        'real_time_queries'
                    ]
                }
            else:
                return start_result
            
        except Exception as e:
            logger.error(f"Failed to setup MCP connection: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def build_mcp_image(self, mcp_dir: str, instance_name: str) -> Dict[str, Any]:
        """Build Docker image for MCP server"""
        try:
            logger.info(f"Building MCP Docker image for {instance_name}")
            
            # Build Docker image
            image_tag = f'mcp-elasticsearch:{instance_name}'
            
            build_process = subprocess.run([
                'docker', 'build', '-t', image_tag, mcp_dir
            ], capture_output=True, text=True)
            
            if build_process.returncode == 0:
                logger.info(f"Docker image built successfully: {image_tag}")
                return {'success': True, 'image_tag': image_tag}
            else:
                logger.error(f"Docker build failed: {build_process.stderr}")
                return {'success': False, 'error': build_process.stderr}
                
        except Exception as e:
            logger.error(f"Build error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def start_mcp_server(self, mcp_dir: str, instance_name: str) -> Dict[str, Any]:
        """Start MCP server using docker-compose"""
        try:
            logger.info(f"Starting MCP server for {instance_name}")
            
            # Start with docker-compose
            compose_process = subprocess.run([
                'docker-compose', '-f', os.path.join(mcp_dir, 'docker-compose.yml'), 
                'up', '-d'
            ], capture_output=True, text=True, cwd=mcp_dir)
            
            if compose_process.returncode == 0:
                # Wait for service to be ready
                await asyncio.sleep(10)
                
                # Test connection
                es_port = self.active_connections.get(instance_name, {}).get('es_port')
                mcp_port = es_port + 1000 if es_port else 8080
                
                logger.info(f"MCP server started successfully on port {mcp_port}")
                return {
                    'success': True,
                    'mcp_port': mcp_port,
                    'message': f'MCP server running for {instance_name}'
                }
            else:
                logger.error(f"Docker compose failed: {compose_process.stderr}")
                return {'success': False, 'error': compose_process.stderr}
                
        except Exception as e:
            logger.error(f"Start error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def stop_mcp_server(self, instance_name: str) -> Dict[str, Any]:
        """Stop MCP server for an instance"""
        try:
            if instance_name not in self.active_connections:
                return {'success': False, 'error': 'Instance not found'}
            
            mcp_dir = f"mcp_configs/{instance_name}"
            
            # Stop with docker-compose
            compose_process = subprocess.run([
                'docker-compose', '-f', os.path.join(mcp_dir, 'docker-compose.yml'), 
                'down'
            ], capture_output=True, text=True, cwd=mcp_dir)
            
            if compose_process.returncode == 0:
                # Remove from active connections
                del self.active_connections[instance_name]
                
                logger.info(f"MCP server stopped for {instance_name}")
                return {
                    'success': True,
                    'message': f'MCP server stopped for {instance_name}'
                }
            else:
                logger.error(f"Failed to stop MCP server: {compose_process.stderr}")
                return {'success': False, 'error': compose_process.stderr}
                
        except Exception as e:
            logger.error(f"Stop error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_active_connections(self) -> Dict[str, Any]:
        """Get all active MCP connections"""
        return self.active_connections
    
    def get_connection_info(self, instance_name: str) -> Optional[Dict[str, Any]]:
        """Get connection info for a specific instance"""
        return self.active_connections.get(instance_name)

# Helper function to test MCP connection
async def test_mcp_connection(mcp_url: str) -> Dict[str, Any]:
    """Test MCP server connection"""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{mcp_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': True,
                        'health_data': data
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Health check failed with status {response.status}'
                    }
                    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
