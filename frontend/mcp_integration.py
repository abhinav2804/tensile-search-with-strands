import asyncio
import json
import logging
import paramiko
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RemoteMCPElasticsearchServer:
    """
    MCP Server that creates Docker containers on the remote VM via SSH
    This runs alongside the Elasticsearch instances on the same remote server
    """
    
    def __init__(self, vm_host="54.227.251.28", vm_user="khemchand", vm_password="wq0XYdUWKa1EN7LI7"):
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.vm_password = vm_password
        self.ssh_client = None
        self.active_connections = {}
        
        logger.info(f"RemoteMCPElasticsearchServer initialized for {vm_host}")
    
    def connect_ssh(self):
        """Establishes an SSH connection to the remote VM."""
        if self.ssh_client:
            return True
        try:
            logger.info(f"Connecting to SSH host: {self.vm_host}")
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.vm_host, username=self.vm_user, password=self.vm_password, timeout=30
            )
            logger.info("SUCCESS: SSH connection established for MCP setup")
            return True
        except Exception as e:
            logger.error(f"ERROR: SSH connection failed for MCP: {e}")
            self.ssh_client = None
            return False
    
    def execute_command(self, command, use_sudo=False):
        """Executes a command on the remote VM via SSH."""
        if use_sudo and not command.startswith('sudo'):
            command = f"sudo {command}"
        
        logger.info(f"Executing MCP command: {command}")
        try:
            if use_sudo:
                full_command = f"echo '{self.vm_password}' | sudo -S {command[5:]}"
                stdin, stdout, stderr = self.ssh_client.exec_command(full_command)
            else:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                
            exit_status = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            if exit_status != 0:
                logger.warning(f"MCP Command exit code: {exit_status}, stderr: {stderr_data.strip()}")
            return exit_status, stdout_data, stderr_data
        except Exception as e:
            logger.error(f"ERROR: MCP Command execution failed: {e}")
            return 1, "", str(e)
    
    def create_mcp_server_files_on_remote(self, instance_name: str, es_port: int):
        """Create MCP server files directly on the remote VM"""
        try:
            logger.info(f"Creating MCP server files on remote VM for {instance_name}")
            
            # Create directory on remote
            self.execute_command(f"mkdir -p /tmp/mcp-{instance_name}")
            
            # Create Dockerfile content
            dockerfile_content = f'''FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install 'elasticsearch>=8.0.0,<9.0.0' aiohttp

COPY mcp_server.py .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "mcp_server.py"]
'''
            
            # Create MCP server Python code
            mcp_server_code = f'''
import asyncio
import json
import logging
from datetime import datetime
from elasticsearch import Elasticsearch
from aiohttp import web
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPElasticsearchHandler:
    def __init__(self):
        self.es_url = "http://{self.vm_host}:{es_port}"
        self.index_name = "{instance_name}"
        self.server_name = "mcp-{instance_name}"
        
        # Initialize Elasticsearch client
        self.es = Elasticsearch([self.es_url], verify_certs=False, request_timeout=30)
        logger.info(f"MCP Server initialized for {{self.es_url}}/{{self.index_name}}")
        
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            if self.es.ping():
                return web.json_response({{
                    "status": "healthy",
                    "elasticsearch_url": self.es_url,
                    "index": self.index_name,
                    "server_name": self.server_name,
                    "timestamp": datetime.now().isoformat(),
                    "mcp_version": "1.0.0"
                }})
            else:
                return web.json_response({{
                    "status": "unhealthy",
                    "error": "Cannot connect to Elasticsearch"
                }}, status=503)
        except Exception as e:
            return web.json_response({{
                "status": "unhealthy",
                "error": str(e)
            }}, status=503)
    
    async def search_documents(self, request):
        """Search documents in Elasticsearch via MCP"""
        try:
            data = await request.json()
            query = data.get("query", "*")
            size = data.get("size", 10)
            
            search_body = {{
                "query": {{
                    "query_string": {{
                        "query": query
                    }}
                }},
                "size": min(size, 100)
            }}
            
            result = self.es.search(index=self.index_name, body=search_body)
            
            return web.json_response({{
                "total_hits": result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"],
                "documents": [hit["_source"] for hit in result["hits"]["hits"]],
                "took": result["took"],
                "index": self.index_name,
                "query": query
            }})
            
        except Exception as e:
            logger.error(f"Search error: {{e}}")
            return web.json_response({{"error": str(e)}}, status=500)
    
    async def get_index_info(self, request):
        """Get comprehensive index information"""
        try:
            # Get index stats
            stats = self.es.indices.stats(index=self.index_name)
            mapping = self.es.indices.get_mapping(index=self.index_name)
            
            return web.json_response({{
                "index": self.index_name,
                "document_count": stats["indices"][self.index_name]["total"]["docs"]["count"],
                "store_size_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "mapping": mapping[self.index_name]["mappings"],
                "server_name": self.server_name,
                "elasticsearch_url": self.es_url
            }})
            
        except Exception as e:
            logger.error(f"Index info error: {{e}}")
            return web.json_response({{"error": str(e)}}, status=500)
    
    async def mcp_capabilities(self, request):
        """MCP protocol capabilities endpoint"""
        return web.json_response({{
            "capabilities": {{
                "search": True,
                "index_info": True,
                "real_time": False,
                "bulk_operations": False
            }},
            "server_info": {{
                "name": self.server_name,
                "version": "1.0.0",
                "elasticsearch_url": self.es_url,
                "index": self.index_name,
                "endpoints": [
                    "GET /health - Health check",
                    "POST /search - Search documents", 
                    "GET /index-info - Index statistics",
                    "GET /capabilities - This endpoint"
                ]
            }},
            "usage": {{
                "search_example": {{
                    "method": "POST",
                    "url": "/search",
                    "body": {{"query": "your search query", "size": 10}}
                }}
            }}
        }})
    
    async def prompt_endpoint(self, request):
        """Direct prompt endpoint for easy querying"""
        try:
            data = await request.json()
            prompt = data.get("prompt", "")
            
            if not prompt:
                return web.json_response({{"error": "No prompt provided"}}, status=400)
            
            # Simple prompt to query conversion
            search_body = {{
                "query": {{
                    "query_string": {{
                        "query": prompt
                    }}
                }},
                "size": 10
            }}
            
            result = self.es.search(index=self.index_name, body=search_body)
            
            return web.json_response({{
                "prompt": prompt,
                "results": {{
                    "total_hits": result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"],
                    "documents": [hit["_source"] for hit in result["hits"]["hits"]],
                    "took": result["took"]
                }},
                "index": self.index_name,
                "timestamp": datetime.now().isoformat()
            }})
            
        except Exception as e:
            logger.error(f"Prompt error: {{e}}")
            return web.json_response({{"error": str(e)}}, status=500)

async def create_app():
    handler = MCPElasticsearchHandler()
    app = web.Application()
    
    # Add routes
    app.router.add_get("/health", handler.health_check)
    app.router.add_post("/search", handler.search_documents)
    app.router.add_get("/index-info", handler.get_index_info)
    app.router.add_get("/capabilities", handler.mcp_capabilities)
    app.router.add_post("/prompt", handler.prompt_endpoint)  # Direct prompt endpoint
    
    return app

if __name__ == "__main__":
    app = asyncio.run(create_app())
    web.run_app(app, host="0.0.0.0", port=8080)
'''
            
            # Write files to remote using echo commands (avoiding file transfer)
            dockerfile_cmd = f"cat > /tmp/mcp-{instance_name}/Dockerfile << 'EOFDF'\n{dockerfile_content}\nEOFDF"
            self.execute_command(dockerfile_cmd)
            
            server_code_cmd = f"cat > /tmp/mcp-{instance_name}/mcp_server.py << 'EOFPY'\n{mcp_server_code}\nEOFPY"
            self.execute_command(server_code_cmd)
            
            logger.info(f"MCP server files created on remote VM for {instance_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create MCP server files: {e}")
            return False
    
    def setup_mcp_connection(self, instance_name: str, es_port: int) -> Dict[str, Any]:
        """
        Setup MCP server connection for a new Elasticsearch instance on remote VM
        """
        try:
            logger.info(f"Setting up remote MCP connection for {instance_name}")
            
            if not self.connect_ssh():
                return {'success': False, 'error': 'Failed to establish SSH connection'}
            
            # Find available MCP port (ES port + 1000)
            mcp_port = es_port + 1000
            
            # Create MCP server files on remote
            if not self.create_mcp_server_files_on_remote(instance_name, es_port):
                return {'success': False, 'error': 'Failed to create MCP server files'}
            
            # Stop any existing MCP container
            self.execute_command(f"docker stop mcp-{instance_name}", use_sudo=True)
            self.execute_command(f"docker rm mcp-{instance_name}", use_sudo=True)
            
            # Build MCP Docker image on remote
            build_cmd = f"docker build -t mcp-{instance_name} /tmp/mcp-{instance_name}"
            exit_status, stdout, stderr = self.execute_command(build_cmd, use_sudo=True)
            
            if exit_status != 0:
                return {'success': False, 'error': f'MCP Docker build failed: {stderr}'}
            
            # Run MCP container on remote
            run_cmd = (
                f"docker run -d --name mcp-{instance_name} "
                f"-p {mcp_port}:8080 "
                f"--restart unless-stopped "
                f"mcp-{instance_name}"
            )
            
            exit_status, stdout, stderr = self.execute_command(run_cmd, use_sudo=True)
            
            if exit_status != 0:
                return {'success': False, 'error': f'MCP container failed to start: {stderr}'}
            
            # Wait for MCP server to start
            logger.info("Waiting for MCP server to initialize...")
            time.sleep(10)
            
            # Test MCP connection
            test_result = self.test_mcp_connection(instance_name, mcp_port)
            
            if test_result['success']:
                mcp_url = f"http://{self.vm_host}:{mcp_port}"
                
                # Store connection info
                self.active_connections[instance_name] = {
                    'es_host': self.vm_host,
                    'es_port': es_port,
                    'mcp_port': mcp_port,
                    'mcp_url': mcp_url,
                    'created_at': datetime.now().isoformat(),
                    'status': 'active'
                }
                
                logger.info(f"MCP server deployed successfully: {mcp_url}")
                
                return {
                    'success': True,
                    'instance_name': instance_name,
                    'mcp_url': mcp_url,
                    'es_url': f'http://{self.vm_host}:{es_port}',
                    'capabilities': [
                        'document_search',
                        'index_information', 
                        'direct_prompts',
                        'real_time_queries'
                    ],
                    'endpoints': {
                        'health': f'{mcp_url}/health',
                        'search': f'{mcp_url}/search',
                        'prompt': f'{mcp_url}/prompt',
                        'capabilities': f'{mcp_url}/capabilities'
                    }
                }
            else:
                return {'success': False, 'error': f'MCP server health check failed: {test_result.get("error")}'}
            
        except Exception as e:
            logger.error(f"Failed to setup remote MCP connection: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_mcp_connection(self, instance_name: str, mcp_port: int) -> Dict[str, Any]:
        """Test MCP server connection"""
        try:
            # Use curl to test the health endpoint
            test_cmd = f"curl -s -f http://localhost:{mcp_port}/health"
            exit_status, stdout, stderr = self.execute_command(test_cmd)
            
            if exit_status == 0:
                logger.info(f"MCP health check passed for {instance_name}")
                return {'success': True, 'health_data': stdout}
            else:
                logger.error(f"MCP health check failed for {instance_name}: {stderr}")
                return {'success': False, 'error': f'Health check failed: {stderr}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_mcp_server(self, instance_name: str) -> Dict[str, Any]:
        """Stop MCP server for an instance"""
        try:
            if not self.connect_ssh():
                return {'success': False, 'error': 'SSH connection failed'}
            
            # Stop MCP container
            exit_status, _, stderr = self.execute_command(f"docker stop mcp-{instance_name}", use_sudo=True)
            
            if exit_status == 0:
                # Remove from active connections
                if instance_name in self.active_connections:
                    del self.active_connections[instance_name]
                
                logger.info(f"MCP server stopped for {instance_name}")
                return {'success': True, 'message': f'MCP server stopped for {instance_name}'}
            else:
                return {'success': False, 'error': f'Failed to stop MCP server: {stderr}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_mcp_server(self, instance_name: str) -> Dict[str, Any]:
        """Delete MCP server and clean up"""
        try:
            if not self.connect_ssh():
                return {'success': False, 'error': 'SSH connection failed'}
            
            # Stop and remove container
            self.execute_command(f"docker stop mcp-{instance_name}", use_sudo=True)
            self.execute_command(f"docker rm mcp-{instance_name}", use_sudo=True)
            
            # Remove image
            self.execute_command(f"docker rmi mcp-{instance_name}", use_sudo=True)
            
            # Clean up files
            self.execute_command(f"rm -rf /tmp/mcp-{instance_name}")
            
            # Remove from active connections
            if instance_name in self.active_connections:
                del self.active_connections[instance_name]
            
            logger.info(f"MCP server deleted for {instance_name}")
            return {'success': True, 'message': f'MCP server deleted for {instance_name}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_active_connections(self) -> Dict[str, Any]:
        """Get all active MCP connections"""
        return {
            'active_connections': self.active_connections,
            'total_count': len(self.active_connections),
            'healthy_count': len([
                conn for conn in self.active_connections.values()
                if conn.get('status') == 'active'
            ])
        }
