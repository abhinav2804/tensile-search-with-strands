import paramiko
import json
import time
import webbrowser
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging
import sys
import os
import pandas as pd
from datetime import datetime

# Import production server config
try:
    from config import PRODUCTION_SERVER
    PROD_HOST = PRODUCTION_SERVER['host']
    PROD_USER = PRODUCTION_SERVER['user']
    PROD_PASS = PRODUCTION_SERVER['password']
    PROD_SSH_KEY = PRODUCTION_SERVER.get('ssh_key_path', None)
except ImportError:
    # Fallback to production server
    PROD_HOST = "82.112.235.26"
    PROD_USER = "root"
    PROD_PASS = "your_password_here"
    PROD_SSH_KEY = None
    print("Warning: Using default production server config")

# Import the remote MCP integration
try:
    from mcp_integration import RemoteMCPElasticsearchServer
    REMOTE_MCP_AVAILABLE = True
    print("Remote MCP integration loaded successfully")
except ImportError as e:
    print(f"Remote MCP integration not available: {e}")
    REMOTE_MCP_AVAILABLE = False

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Helper Classes ---

class EnhancedSchemaManager:
    """A class to handle schema generation for Elasticsearch."""
    def __init__(self):
        logger.info("EnhancedSchemaManager initialized.")
    
    def generate_schema(self, documents):
        """Generates a basic Elasticsearch schema from a list of documents."""
        logger.info("Generating a basic schema...")
        properties = {}
        if not documents:
            return {"mappings": {"properties": {}}}
            
        sample = documents[0]
        for key, value in sample.items():
            # CRITICAL: Check boolean BEFORE numeric! In Python, bool is subclass of int
            if isinstance(value, bool):
                properties[key] = {"type": "boolean"}
            elif isinstance(value, (int, float)):
                properties[key] = {"type": "double"}
            else:
                properties[key] = {
                    "type": "text",
                    "fields": { "keyword": { "type": "keyword", "ignore_above": 256 } }
                }
        logger.info(f"Generated schema with {len(properties)} fields.")
        return {"mappings": {"properties": properties}}

class FixedRemoteElasticsearchManager:
    """Placeholder class to satisfy the import in app.py."""
    def __init__(self):
        logger.info("FixedRemoteElasticsearchManager initialized (placeholder).")

# --- Enhanced Remote Deployment with MCP Integration ---

class RemoteElasticsearchManager:
    """Enhanced Remote ES manager with integrated MCP server deployment"""
    
    def __init__(self, vm_host=None, vm_user=None, vm_password=None):
        # Use production server config by default
        self.vm_host = vm_host or PROD_HOST
        self.vm_user = vm_user or PROD_USER
        self.vm_password = vm_password or PROD_PASS
        self.ssh_key = PROD_SSH_KEY
        self.ssh_client = None
        
        # Initialize MCP server integration
        if REMOTE_MCP_AVAILABLE:
            self.mcp_server = RemoteMCPElasticsearchServer(self.vm_host, self.vm_user, self.vm_password)
            self.mcp_enabled = True
            logger.info("Remote MCP integration enabled")
        else:
            self.mcp_server = None
            self.mcp_enabled = False
            logger.info("Remote MCP integration disabled - fallback mode")
        
        logger.info(f"RemoteElasticsearchManager initialized for PRODUCTION: {self.vm_host}")
        logger.info(f"🚀 Deploying to: {self.vm_host} (Production Server)")
        
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
            logger.info("SUCCESS: SSH connection established.")
            return True
        except Exception as e:
            logger.error(f"ERROR: SSH connection failed: {e}")
            self.ssh_client = None
            return False
    
    def disconnect_ssh(self):
        """Closes the SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
            logger.info("SSH connection closed.")
    
    def execute_command(self, command, use_sudo=False):
        """Executes a command on the remote VM."""
        if use_sudo and not command.startswith('sudo'):
            command = f"sudo {command}"
        
        logger.info(f"Executing remote command: {command}")
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
                logger.warning(f"Command exit code: {exit_status}, stderr: {stderr_data.strip()}")
            return exit_status, stdout_data, stderr_data
        except Exception as e:
            logger.error(f"ERROR: Command execution failed: {e}")
            return 1, "", str(e)

    def create_new_elasticsearch_instance(self, instance_name, index_data, schema):
        """Creates ES instance and automatically sets up MCP server"""
        logger.info(f"Starting enhanced remote deployment for instance: {instance_name}")
        if not self.connect_ssh():
            return {'success': False, 'error': 'Failed to establish SSH connection'}

        available_port = self._find_available_port()
        
        # Cleanup previous container if it exists
        self.execute_command(f"docker stop {instance_name}", use_sudo=True)
        self.execute_command(f"docker rm {instance_name}", use_sudo=True)

        # Deploy Elasticsearch instance
        docker_run_cmd = (
            f'docker run -d --name {instance_name} -p {available_port}:9200 '
            f'-e "discovery.type=single-node" -e "xpack.security.enabled=false" '
            f'-e "ES_JAVA_OPTS=-Xms512m -Xmx512m" '
            f'elasticsearch:8.15.0'
        )
        
        exit_status, _, stderr = self.execute_command(docker_run_cmd, use_sudo=True)
        if exit_status != 0:
            return {'success': False, 'error': f'ES Container failed to start: {stderr}'}

        logger.info("Waiting for Elasticsearch to initialize...")
        time.sleep(45)

        # Upload data to ES instance
        upload_success = self._upload_data_to_instance(index_data, schema, available_port)
        if not upload_success:
            return {'success': False, 'error': 'Failed to upload data to ES instance'}

        # Base ES deployment result
        es_result = {
            'success': True, 
            'host': self.vm_host, 
            'port': available_port,
            'instance_name': instance_name, 
            'access_url': f"http://{self.vm_host}:{available_port}",
            'documents_deployed': sum(len(docs) for docs in index_data.values())
        }

        # Set up MCP integration if available
        mcp_result = {'success': False, 'error': 'MCP integration not available'}
        
        if self.mcp_enabled and self.mcp_server:
            logger.info("Setting up MCP server alongside Elasticsearch instance...")
            try:
                mcp_result = self.mcp_server.setup_mcp_connection(instance_name, available_port)
                
                if mcp_result['success']:
                    logger.info(f"SUCCESS: MCP server deployed at {mcp_result['mcp_url']}")
                    logger.info(f"MCP Prompt endpoint: {mcp_result['mcp_url']}/prompt")
                else:
                    logger.warning(f"MCP setup failed: {mcp_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"MCP setup exception: {e}")
                mcp_result = {'success': False, 'error': str(e)}

        # Combine results
        es_result['mcp_integration'] = mcp_result
        
        if mcp_result['success']:
            es_result['mcp_url'] = mcp_result['mcp_url']
            es_result['mcp_prompt_url'] = f"{mcp_result['mcp_url']}/prompt"
            es_result['mcp_capabilities'] = mcp_result.get('capabilities', [])
            
        logger.info("SUCCESS: Enhanced remote deployment complete.")
        return es_result

    def _find_available_port(self):
        base_port = 9200
        for port in range(base_port, base_port + 100):
            exit_status, _, _ = self.execute_command(f"netstat -tuln | grep ':{port} '")
            if exit_status != 0:
                logger.info(f"Found available port: {port}")
                return port
        return 9300

    def _upload_data_to_instance(self, index_data, schema, port):
        try:
            # Use SSH tunnel for external connections (firewall bypassed)
            import socket
            import select
            
            # Create SSH tunnel: local port forwards to remote localhost:port
            local_port = 19200 + (port - 9200)  # e.g., 9202 -> 19202
            
            # Check if we can reach the remote server directly (for debugging)
            # If not reachable externally, use SSH to execute commands remotely
            logger.info(f"Testing connection to remote Elasticsearch on port {port}...")
            
            # Try connecting via SSH - execute indexing on the remote server itself
            logger.info(f"Using SSH execution method for data upload to port {port}")
            
            # First, test if ES is ready on the remote server (via SSH)
            logger.info(f"Checking if Elasticsearch is ready on localhost:{port} (via SSH)...")
            for i in range(15):  # Retry up to 15 times (75 seconds total)
                exit_code, stdout, stderr = self.execute_command(f"curl -s http://localhost:{port}/_cluster/health")
                if exit_code == 0 and '"status"' in stdout:
                    logger.info(f"✅ Elasticsearch is ready on remote localhost:{port}!")
                    break
                logger.info(f"   Attempt {i+1}/15: Elasticsearch not ready yet, waiting 5 seconds...")
                time.sleep(5)
            else:
                logger.error("Could not ping remote Elasticsearch instance after 15 attempts.")
                return False

            # Now upload data via SSH tunnel - use forwarded local port
            logger.info(f"Creating temporary SSH tunnel for data upload...")
            import threading
            import subprocess
            
            # Use SSH to create port forward in background
            # This forwards local port to remote localhost:port
            local_port = 19200 + (port - 9200)
            
            # Build SSH command based on whether we have SSH key
            ssh_cmd = ['ssh', '-N', '-L', f'{local_port}:localhost:{port}',
                       f'{self.vm_user}@{self.vm_host}',
                       '-o', 'StrictHostKeyChecking=no']
            
            if self.ssh_key:
                ssh_cmd.extend(['-i', self.ssh_key])
            
            tunnel_process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give tunnel a moment to establish
            time.sleep(2)
            
            try:
                # Connect via the SSH tunnel
                es_url = f"http://localhost:{local_port}"
                es_client = Elasticsearch([es_url], verify_certs=False, request_timeout=60)
                
                logger.info(f"Uploading data via SSH tunnel to {es_url}...")
                for index_name, documents in index_data.items():
                    logger.info(f"Creating index: {index_name}")
                    es_client.indices.create(index=index_name, body=schema, ignore=400)
                    
                    logger.info(f"Bulk uploading {len(documents)} documents...")
                    actions = [{'_index': index_name, '_source': doc} for doc in documents]
                    bulk(es_client, actions)
                    
                    logger.info(f"Refreshing index...")
                    es_client.indices.refresh(index=index_name)
                    
                logger.info(f"✅ Data upload completed successfully!")
                return True
            finally:
                # Clean up SSH tunnel
                tunnel_process.terminate()
                tunnel_process.wait(timeout=5)
            return True
        except Exception as e:
            logger.error(f"ERROR: Data upload failed: {e}")
            return False
            
    def list_instances(self):
        """List instances with MCP status"""
        if not self.connect_ssh(): 
            return []
            
        exit_status, stdout, _ = self.execute_command("docker ps --filter ancestor=elasticsearch:8.15.0 --format '{{.Names}}\t{{.Ports}}'")
        instances = []
        
        if exit_status == 0:
            for line in stdout.strip().split('\n'):
                if not line or '\t' not in line: 
                    continue
                    
                name, ports = line.split('\t')
                port = ports.split('->')[0].split(':')[-1]
                
                instance_info = {
                    'name': name, 
                    'port': port, 
                    'host': self.vm_host, 
                    'url': f"http://{self.vm_host}:{port}",
                    'mcp_status': 'not_configured',
                    'mcp_url': None
                }
                
                # Check MCP status if available
                if self.mcp_enabled and self.mcp_server:
                    mcp_connections = self.mcp_server.get_active_connections()
                    if name in mcp_connections.get('active_connections', {}):
                        mcp_info = mcp_connections['active_connections'][name]
                        instance_info['mcp_status'] = mcp_info.get('status', 'unknown')
                        instance_info['mcp_url'] = mcp_info.get('mcp_url')
                        instance_info['mcp_prompt_url'] = f"{mcp_info.get('mcp_url')}/prompt" if mcp_info.get('mcp_url') else None
                
                instances.append(instance_info)
                
        return instances

    def stop_instance(self, instance_name):
        """Stop ES instance and its MCP server"""
        if not self.connect_ssh(): 
            return False
            
        # Stop MCP server first if available
        if self.mcp_enabled and self.mcp_server:
            mcp_result = self.mcp_server.stop_mcp_server(instance_name)
            if mcp_result['success']:
                logger.info(f"MCP server stopped for {instance_name}")
        
        # Stop ES instance
        exit_status, _, _ = self.execute_command(f"docker stop {instance_name}", use_sudo=True)
        return exit_status == 0

    def delete_instance(self, instance_name):
        """Delete ES instance and its MCP components"""
        if not self.connect_ssh(): 
            return False
            
        # Delete MCP server first if available
        if self.mcp_enabled and self.mcp_server:
            mcp_result = self.mcp_server.delete_mcp_server(instance_name)
            if mcp_result['success']:
                logger.info(f"MCP server deleted for {instance_name}")
        
        # Stop and delete ES instance
        self.stop_instance(instance_name)
        exit_status, _, _ = self.execute_command(f"docker rm {instance_name}", use_sudo=True)
        return exit_status == 0

    def get_mcp_connections(self):
        """Get MCP connection information"""
        if self.mcp_enabled and self.mcp_server:
            return self.mcp_server.get_active_connections()
        return {'active_connections': {}, 'total_count': 0, 'healthy_count': 0}

    def test_mcp_connection(self, instance_name):
        """Test MCP connection for an instance"""
        if self.mcp_enabled and self.mcp_server:
            mcp_connections = self.mcp_server.get_active_connections()
            if instance_name in mcp_connections.get('active_connections', {}):
                mcp_info = mcp_connections['active_connections'][instance_name]
                mcp_port = mcp_info.get('mcp_port')
                if mcp_port:
                    return self.mcp_server.test_mcp_connection(instance_name, mcp_port)
        return {'success': False, 'error': 'MCP integration not available or instance not found'}


# --- Main Pipeline Class ---

class EnhancedDataPipeline:
    """The main pipeline class with enhanced remote MCP integration"""
    def __init__(self, aws_access_key, aws_secret_key, aws_region, es_host, es_auth):
        # Initialize remote manager with MCP integration
        self.remote_manager = RemoteElasticsearchManager()
        
        # Initialize local ES manager
        self.es_manager = self.LocalESManager(es_host, es_auth)
        
        # For schema handling
        self.schema_manager = EnhancedSchemaManager()
        
        # MCP status
        self.mcp_enabled = self.remote_manager.mcp_enabled
        
        logger.info(f"EnhancedDataPipeline initialized. Remote MCP enabled: {self.mcp_enabled}")

    class LocalESManager:
        """Local ES manager (unchanged for now)"""
        def __init__(self, host, auth):
            try:
                self.es = Elasticsearch(hosts=[host], http_auth=auth, timeout=2, max_retries=0, request_timeout=2)
                # Quick ping with minimal timeout to avoid Flask startup delays
                try:
                    if not self.es.ping(request_timeout=2):
                        raise ConnectionError("Could not connect to local Elasticsearch")
                    logger.info(f"Connected to local Elasticsearch at {host}")
                except (ConnectionError, Exception) as ping_error:
                    logger.warning(f"Local Elasticsearch not available: {ping_error}")
                    self.es = None
            except Exception as e:
                self.es = None
                logger.error(f"Failed to initialize local Elasticsearch: {e}")

    def _parse_file(self, file_path):
        """Parses JSON or CSV files into a list of dictionaries."""
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif ext.lower() == '.csv':
            df = pd.read_csv(file_path)
            return df.where(pd.notnull(df), None).to_dict('records')
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def process_file_enhanced(self, file_path, index_name, schema_file, user_queries, deploy_remote):
        """Enhanced processing function with remote MCP integration"""
        try:
            documents = self._parse_file(file_path)
            if not documents:
                return {'success': False, 'error': 'No documents found in file'}
            
            schema = self.schema_manager.generate_schema(documents)
            
            os.makedirs('schemas', exist_ok=True)
            domain_info = {
                "domain": "auto-detected",
                "templates": [],
                "auto_queries": user_queries
            }
            with open(schema_file, 'w') as f:
                json.dump({"schema": schema, "auto_queries": user_queries}, f, indent=4)
            
            deployment_result = None
            local_indexing_success = False
            
            if deploy_remote:
                logger.info("Deploying to remote server with MCP integration")
                index_data = {index_name: documents}
                deployment_result = self.remote_manager.create_new_elasticsearch_instance(
                    instance_name=index_name, index_data=index_data, schema=schema
                )
                
                # Log MCP integration results
                if deployment_result.get('success'):
                    mcp_integration = deployment_result.get('mcp_integration', {})
                    if mcp_integration.get('success'):
                        logger.info(f"SUCCESS: MCP server available at {mcp_integration.get('mcp_url')}")
                        logger.info(f"SUCCESS: Direct prompt endpoint at {deployment_result.get('mcp_prompt_url')}")
                    else:
                        logger.warning(f"MCP integration failed: {mcp_integration.get('error')}")
                
            else:
                logger.info("Deploying locally (MCP integration not available for local)")
                
                if not self.es_manager.es:
                    raise ConnectionError("Local Elasticsearch is not available.")
                
                if self.es_manager.es.indices.exists(index=index_name):
                    self.es_manager.es.indices.delete(index=index_name)
                
                self.es_manager.es.indices.create(index=index_name, body=schema)
                actions = [{'_index': index_name, '_source': doc} for doc in documents]
                bulk(self.es_manager.es, actions)
                self.es_manager.es.indices.refresh(index=index_name)
                local_indexing_success = True
                logger.info("Local indexing completed successfully (without MCP)")

            return {
                'domain_info': domain_info, 
                'total_documents': len(documents),
                'auto_queries_generated': len(user_queries),
                'attributes_extracted': len(schema['mappings']['properties']),
                'schema_optimized': True, 
                'deployment_result': deployment_result,
                'local_indexing_success': local_indexing_success,
                'mcp_enabled': self.mcp_enabled
            }
        except Exception as e:
            logger.error(f"Error in process_file_enhanced: {e}", exc_info=True)
            raise

    def get_remote_instances(self):
        return self.remote_manager.list_instances()

    def stop_remote_instance(self, instance_name):
        return self.remote_manager.stop_instance(instance_name)

    def delete_remote_instance(self, instance_name):
        return self.remote_manager.delete_instance(instance_name)

    def get_mcp_connections(self):
        """Get MCP connection information"""
        return self.remote_manager.get_mcp_connections()

    def test_mcp_connection(self, instance_name):
        """Test MCP connection for an instance"""
        return self.remote_manager.test_mcp_connection(instance_name)
