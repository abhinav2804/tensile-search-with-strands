from flask import Flask, jsonify, request, render_template_string
import paramiko
import json
import time
import webbrowser
from elasticsearch import Elasticsearch
import subprocess
import logging
import sys

app = Flask(__name__)

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RemoteElasticsearchManager:
    """Manage Elasticsearch deployment on remote VM with Docker - Enhanced Logging"""
    
    def __init__(self, vm_host="54.227.251.28", vm_user="khemchand", vm_password="wq0XYdUWKa1EN7LI7"):
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.vm_password = vm_password
        self.ssh_client = None
        self.es_port = 9200
        self.instance_name = None
        logger.info(f"RemoteElasticsearchManager initialized for {vm_host}")
        
    def connect_ssh(self):
        """Establish SSH connection to VM with detailed logging"""
        logger.info("=" * 60)
        logger.info("STEP 1: ESTABLISHING SSH CONNECTION")
        logger.info("=" * 60)
        
        try:
            logger.info(f"Connecting to SSH host: {self.vm_host}")
            logger.info(f"Username: {self.vm_user}")
            logger.info("Initializing SSH client...")
            
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info("Attempting SSH connection...")
            self.ssh_client.connect(
                hostname=self.vm_host,
                username=self.vm_user,
                password=self.vm_password,
                timeout=30,
                auth_timeout=30,
                banner_timeout=30
            )
            
            logger.info("SUCCESS: SSH connection established successfully!")
            
            # Test basic connectivity
            logger.info("Testing SSH connection with 'whoami' command...")
            exit_status, stdout, stderr = self.execute_command("whoami")
            if exit_status == 0:
                logger.info(f"SUCCESS: SSH test successful. Connected as user: {stdout.strip()}")
            else:
                logger.warning(f"SSH test warning: {stderr}")
            
            return True
            
        except paramiko.AuthenticationException:
            logger.error("ERROR: SSH Authentication failed - Check username/password")
            return False
        except paramiko.SSHException as e:
            logger.error(f"ERROR: SSH connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"ERROR: Unexpected SSH error: {e}")
            return False
    
    def disconnect_ssh(self):
        """Close SSH connection"""
        if self.ssh_client:
            logger.info("Closing SSH connection...")
            self.ssh_client.close()
            self.ssh_client = None
            logger.info("SUCCESS: SSH connection closed")
    
    def execute_command(self, command: str, use_sudo=False) -> tuple:
        """Execute command on remote VM with detailed logging"""
        if use_sudo and not command.startswith('sudo'):
            command = f"sudo {command}"
            
        logger.info(f"Executing: {command}")
        
        try:
            if use_sudo and command.startswith('sudo'):
                # Use expect-like approach for sudo commands
                full_command = f"echo '{self.vm_password}' | sudo -S {command[5:]}"
                stdin, stdout, stderr = self.ssh_client.exec_command(full_command)
                exit_status = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                
                if exit_status == 0:
                    logger.info(f"SUCCESS: Command successful")
                    if stdout_data.strip():
                        logger.info(f"Output: {stdout_data.strip()[:200]}")
                else:
                    logger.warning(f"WARNING: Command exit code: {exit_status}")
                    if stderr_data.strip():
                        logger.warning(f"Error: {stderr_data.strip()[:200]}")
                        
                return exit_status, stdout_data, stderr_data
            else:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                
                if exit_status == 0:
                    logger.info(f"SUCCESS: Command successful")
                    if stdout_data.strip():
                        logger.info(f"Output: {stdout_data.strip()[:200]}")
                else:
                    logger.warning(f"WARNING: Command exit code: {exit_status}")
                    if stderr_data.strip():
                        logger.warning(f"Error: {stderr_data.strip()[:200]}")
                
                return exit_status, stdout_data, stderr_data
                
        except Exception as e:
            logger.error(f"ERROR: Command execution failed: {e}")
            return 1, "", str(e)
    
    def setup_docker_environment(self):
        """Setup Docker and Elasticsearch using Docker with detailed logging"""
        logger.info("=" * 60)
        logger.info("STEP 2: SETTING UP DOCKER ENVIRONMENT")
        logger.info("=" * 60)
        
        # Check if Docker is already installed
        logger.info("Checking if Docker is already installed...")
        exit_status, stdout, stderr = self.execute_command("docker --version")
        
        if exit_status == 0:
            logger.info(f"SUCCESS: Docker already installed: {stdout.strip()}")
        else:
            logger.info("Docker not found, installing Docker...")
            
            setup_commands = [
                ("Updating package list", "apt-get update"),
                ("Installing Docker.io", "apt-get install -y docker.io"),
                ("Starting Docker service", "systemctl start docker"),
                ("Enabling Docker service", "systemctl enable docker"),
                ("Adding user to docker group", f"usermod -aG docker {self.vm_user}"),
            ]
            
            for description, cmd in setup_commands:
                logger.info(f"RUNNING: {description}...")
                exit_status, stdout, stderr = self.execute_command(cmd, use_sudo=True)
                
                if exit_status != 0:
                    logger.warning(f"WARNING: {description} had warnings: {stderr[:100]}")
                else:
                    logger.info(f"SUCCESS: {description} completed")
        
        # Check Docker daemon status
        logger.info("Checking Docker daemon status...")
        exit_status, stdout, stderr = self.execute_command("systemctl is-active docker", use_sudo=True)
        if exit_status == 0:
            logger.info(f"SUCCESS: Docker daemon is active: {stdout.strip()}")
        else:
            logger.info("Starting Docker daemon...")
            self.execute_command("systemctl start docker", use_sudo=True)
        
        # Pull Elasticsearch image
        logger.info("DOCKER: Pulling Elasticsearch Docker image...")
        logger.info("This may take a few minutes for first time...")
        exit_status, stdout, stderr = self.execute_command("docker pull elasticsearch:8.15.0")
        
        if exit_status == 0:
            logger.info("SUCCESS: Elasticsearch image pulled successfully")
        else:
            logger.warning(f"WARNING: Image pull had issues: {stderr[:200]}")
        
        # Create data directory
        logger.info("FILESYSTEM: Creating Elasticsearch data directory...")
        data_commands = [
            ("Creating data directory", "mkdir -p /opt/elasticsearch-data"),
            ("Setting ownership", f"chown -R {self.vm_user}:{self.vm_user} /opt/elasticsearch-data")
        ]
        
        for description, cmd in data_commands:
            logger.info(f"FILESYSTEM: {description}...")
            exit_status, stdout, stderr = self.execute_command(cmd, use_sudo=True)
            if exit_status == 0:
                logger.info(f"SUCCESS: {description} completed")
    
    def create_new_elasticsearch_instance(self, instance_name: str, index_data: dict, schema: dict):
        """Create a new Elasticsearch instance using Docker with comprehensive logging"""
        logger.info("=" * 80)
        logger.info("STARTING REMOTE ELASTICSEARCH DEPLOYMENT")
        logger.info("=" * 80)
        
        self.instance_name = instance_name
        logger.info(f"Instance name: {instance_name}")
        logger.info(f"Documents to upload: {sum(len(docs) for docs in index_data.values())}")
        
        # Find available port
        logger.info("NETWORK: Finding available port...")
        available_port = self._find_available_port()
        self.es_port = available_port
        logger.info(f"SUCCESS: Selected port: {available_port}")
        
        # Setup Docker environment
        self.setup_docker_environment()
        
        logger.info("=" * 60)
        logger.info("STEP 3: CREATING ELASTICSEARCH CONTAINER")
        logger.info("=" * 60)
        
        # Stop any existing container with same name
        logger.info(f"CLEANUP: Cleaning up existing container: {instance_name}")
        stop_cmd = f"docker stop {instance_name}"
        remove_cmd = f"docker rm {instance_name}"
        
        self.execute_command(stop_cmd)
        self.execute_command(remove_cmd)
        logger.info("SUCCESS: Cleanup completed")
        
        # Create and run Elasticsearch container
        docker_run_cmd = f"""docker run -d \
            --name {instance_name} \
            -p {available_port}:9200 \
            -p {available_port + 100}:9300 \
            -e "discovery.type=single-node" \
            -e "xpack.security.enabled=false" \
            -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
            --user 1000:1000 \
            -v /opt/elasticsearch-data/{instance_name}:/usr/share/elasticsearch/data:Z \
            elasticsearch:8.15.0"""
        
        # First create and set permissions for the data directory
        logger.info("SETUP: Creating and setting permissions for data directory...")
        data_setup_commands = [
            f"mkdir -p /opt/elasticsearch-data/{instance_name}",
            f"chown -R 1000:1000 /opt/elasticsearch-data/{instance_name}",
            f"chmod -R 777 /opt/elasticsearch-data/{instance_name}"
        ]
        
        for cmd in data_setup_commands:
            logger.info(f"PERMISSIONS: Executing: {cmd}")
            exit_status, stdout, stderr = self.execute_command(cmd, use_sudo=True)
            if exit_status == 0:
                logger.info("SUCCESS: Permission command completed")
            else:
                logger.warning(f"WARNING: Permission command had issues: {stderr[:100]}")
        
        logger.info("DOCKER: Starting Elasticsearch container...")
        logger.info(f"Container port mapping: {available_port}:9200")
        
        exit_status, stdout, stderr = self.execute_command(docker_run_cmd)
        
        if exit_status != 0:
            logger.error(f"ERROR: Failed to start container: {stderr}")
            return {'success': False, 'error': f'Container failed to start: {stderr}'}
        
        container_id = stdout.strip()
        logger.info(f"SUCCESS: Container started with ID: {container_id[:12]}...")
        
        # Wait for Elasticsearch to start
        logger.info("WAITING: Waiting for Elasticsearch to initialize...")
        logger.info("This typically takes 30-60 seconds...")
        
        for i in range(12):  # 60 seconds total
            time.sleep(5)
            logger.info(f"Waiting... ({(i+1)*5}s)")
            
            # Check if container is still running
            check_cmd = f"docker ps | grep {instance_name}"
            exit_status, stdout, stderr = self.execute_command(check_cmd)
            
            if exit_status == 0 and instance_name in stdout:
                logger.info(f"SUCCESS: Container is running (attempt {i+1})")
                break
            else:
                logger.warning(f"WARNING: Container check failed (attempt {i+1})")
        else:
            # Check logs for debugging
            logger.error("ERROR: Container failed to start properly")
            logs_cmd = f"docker logs {instance_name}"
            _, logs, _ = self.execute_command(logs_cmd)
            logger.error(f"Container logs: {logs[:500]}...")
            return {'success': False, 'error': f'Container not running. Check logs: {logs[:200]}'}
        
        # Test Elasticsearch endpoint
        logger.info("TESTING: Testing Elasticsearch endpoint...")
        test_cmd = f"curl -s http://localhost:{available_port}/_cluster/health"
        exit_status, health_response, _ = self.execute_command(test_cmd)
        
        if exit_status == 0:
            logger.info(f"SUCCESS: Elasticsearch health check passed")
            logger.info(f"Health status: {health_response.strip()[:100]}...")
        else:
            logger.warning("WARNING: Health check failed, but continuing with data upload")
        
        # Upload data
        logger.info("=" * 60)
        logger.info("STEP 4: UPLOADING DATA TO ELASTICSEARCH")
        logger.info("=" * 60)
        
        success = self._upload_data_to_instance(index_data, schema, available_port)
        
        if success:
            access_url = f"http://{self.vm_host}:{available_port}"
            logger.info("=" * 80)
            logger.info("DEPLOYMENT SUCCESSFUL!")
            logger.info("=" * 80)
            logger.info(f"SUCCESS: Elasticsearch instance created at: {access_url}")
            logger.info(f"SUCCESS: Container name: {instance_name}")
            logger.info(f"SUCCESS: Port: {available_port}")
            logger.info("BROWSER: Opening browser automatically...")
            
            # Open browser automatically
            try:
                webbrowser.open(access_url)
                logger.info("SUCCESS: Browser opened successfully")
            except Exception as e:
                logger.warning(f"WARNING: Failed to open browser: {e}")
            
            return {
                'success': True,
                'host': self.vm_host,
                'port': available_port,
                'instance_name': instance_name,
                'index_name': list(index_data.keys())[0] if index_data else None,
                'access_url': access_url,
                'browser_opened': True,
                'container_id': instance_name
            }
        else:
            logger.error("ERROR: Data upload failed")
            return {'success': False, 'error': 'Failed to upload data'}
    
    def _find_available_port(self) -> int:
        """Find an available port on the VM with logging"""
        base_port = 9200
        logger.info(f"Checking for available ports starting from {base_port}...")
        
        for port in range(base_port, base_port + 100):
            exit_status, stdout, stderr = self.execute_command(f"netstat -tuln | grep :{port}")
            if exit_status != 0 or not stdout.strip():
                logger.info(f"SUCCESS: Port {port} is available")
                return port
            else:
                logger.info(f"Port {port} is in use")
        
        logger.warning(f"Using fallback port 9300")
        return 9300  # Fallback port
    
    def _upload_data_to_instance(self, index_data: dict, schema: dict, port: int) -> bool:
        """Upload data to the new Elasticsearch instance with detailed logging"""
        try:
            # Connect to the new Elasticsearch instance
            es_url = f"http://{self.vm_host}:{port}"
            logger.info(f"CONNECTION: Connecting to Elasticsearch at: {es_url}")
            
            es_client = Elasticsearch([es_url], verify_certs=False, timeout=60)
            
            # Wait for ES to be ready with multiple attempts
            logger.info("WAITING: Waiting for Elasticsearch to accept connections...")
            
            for i in range(30):
                try:
                    if es_client.ping():
                        logger.info(f"SUCCESS: Elasticsearch is ready! (attempt {i+1})")
                        
                        # Get cluster info
                        try:
                            info = es_client.info()
                            logger.info(f"Cluster name: {info.get('cluster_name', 'unknown')}")
                            logger.info(f"ES version: {info.get('version', {}).get('number', 'unknown')}")
                        except:
                            pass
                        
                        break
                except Exception as e:
                    logger.info(f"Connection attempt {i+1}/30 failed: {str(e)[:50]}...")
                    time.sleep(5)
            else:
                logger.error("ERROR: Elasticsearch failed to become ready after 150 seconds")
                return False
            
            # Create indices and upload data
            total_uploaded = 0
            for index_name, documents in index_data.items():
                logger.info(f"INDEX: Processing index: {index_name}")
                logger.info(f"INDEX: Documents to upload: {len(documents)}")
                
                # Create index with schema
                try:
                    logger.info("SCHEMA: Creating index with schema...")
                    es_client.indices.create(index=index_name, body=schema, ignore=400)
                    logger.info("SUCCESS: Index created successfully")
                except Exception as e:
                    logger.warning(f"WARNING: Index creation warning: {str(e)[:100]}...")
                
                # Bulk upload documents
                logger.info("UPLOAD: Starting bulk document upload...")
                from elasticsearch.helpers import bulk
                
                actions = []
                for i, doc in enumerate(documents):
                    actions.append({
                        '_index': index_name,
                        '_id': f"{index_name}_{i}",
                        '_source': doc
                    })
                
                # Upload in batches
                batch_size = 100
                batches_total = (len(actions) + batch_size - 1) // batch_size
                logger.info(f"BATCHES: Uploading {batches_total} batches of {batch_size} documents each")
                
                for i in range(0, len(actions), batch_size):
                    batch_num = i // batch_size + 1
                    batch = actions[i:i+batch_size]
                    
                    try:
                        success, failed = bulk(es_client, batch, chunk_size=batch_size, request_timeout=60)
                        total_uploaded += success
                        logger.info(f"SUCCESS: Batch {batch_num}/{batches_total}: {success} documents uploaded")
                        
                        if failed:
                            logger.warning(f"WARNING: Batch {batch_num}: {len(failed)} documents failed")
                            
                    except Exception as e:
                        logger.warning(f"ERROR: Batch {batch_num} upload failed: {str(e)[:100]}...")
                
                logger.info(f"SUCCESS: Total uploaded to {index_name}: {total_uploaded} documents")
                
                # Refresh index
                logger.info("REFRESH: Refreshing index to make documents searchable...")
                es_client.indices.refresh(index=index_name)
                logger.info("SUCCESS: Index refreshed")
                
                # Verify document count
                try:
                    count_result = es_client.count(index=index_name)
                    actual_count = count_result['count']
                    logger.info(f"SUCCESS: Verification: {actual_count} documents are searchable")
                except Exception as e:
                    logger.warning(f"WARNING: Could not verify document count: {e}")
            
            logger.info(f"COMPLETE: All data uploaded successfully! Total documents: {total_uploaded}")
            return True
            
        except Exception as e:
            logger.error(f"ERROR: Data upload failed: {e}")
            return False

class RemoteElasticsearchManager:
    """Manage Elasticsearch deployment on remote VM with Docker - Enhanced Logging"""
    
    def __init__(self, vm_host="54.227.251.28", vm_user="khemchand", vm_password="wq0XYdUWKa1EN7LI7"):
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.vm_password = vm_password
        self.ssh_client = None
        self.es_port = 9200
        self.instance_name = None
        logger.info(f"RemoteElasticsearchManager initialized for {vm_host}")
        
    def connect_ssh(self):
        """Establish SSH connection to VM with detailed logging"""
        logger.info("=" * 60)
        logger.info("STEP 1: ESTABLISHING SSH CONNECTION")
        logger.info("=" * 60)
        
        try:
            logger.info(f"Connecting to SSH host: {self.vm_host}")
            logger.info(f"Username: {self.vm_user}")
            logger.info("Initializing SSH client...")
            
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info("Attempting SSH connection...")
            self.ssh_client.connect(
                hostname=self.vm_host,
                username=self.vm_user,
                password=self.vm_password,
                timeout=30,
                auth_timeout=30,
                banner_timeout=30
            )
            
            logger.info("✅ SSH connection established successfully!")
            
            # Test basic connectivity
            logger.info("Testing SSH connection with 'whoami' command...")
            exit_status, stdout, stderr = self.execute_command("whoami")
            if exit_status == 0:
                logger.info(f"✅ SSH test successful. Connected as user: {stdout.strip()}")
            else:
                logger.warning(f"SSH test warning: {stderr}")
            
            return True
            
        except paramiko.AuthenticationException:
            logger.error("❌ SSH Authentication failed - Check username/password")
            return False
        except paramiko.SSHException as e:
            logger.error(f"❌ SSH connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected SSH error: {e}")
            return False
    
    def disconnect_ssh(self):
        """Close SSH connection"""
        if self.ssh_client:
            logger.info("Closing SSH connection...")
            self.ssh_client.close()
            self.ssh_client = None
            logger.info("✅ SSH connection closed")
    
    def execute_command(self, command: str, use_sudo=False) -> tuple:
        """Execute command on remote VM with detailed logging"""
        if use_sudo and not command.startswith('sudo'):
            command = f"sudo {command}"
            
        logger.info(f"Executing: {command}")
        
        try:
            if use_sudo and command.startswith('sudo'):
                # Use expect-like approach for sudo commands
                full_command = f"echo '{self.vm_password}' | sudo -S {command[5:]}"
                stdin, stdout, stderr = self.ssh_client.exec_command(full_command)
                exit_status = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                
                if exit_status == 0:
                    logger.info(f"✅ Command successful")
                    if stdout_data.strip():
                        logger.info(f"Output: {stdout_data.strip()[:200]}")
                else:
                    logger.warning(f"⚠️ Command exit code: {exit_status}")
                    if stderr_data.strip():
                        logger.warning(f"Error: {stderr_data.strip()[:200]}")
                        
                return exit_status, stdout_data, stderr_data
            else:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                
                if exit_status == 0:
                    logger.info(f"✅ Command successful")
                    if stdout_data.strip():
                        logger.info(f"Output: {stdout_data.strip()[:200]}")
                else:
                    logger.warning(f"⚠️ Command exit code: {exit_status}")
                    if stderr_data.strip():
                        logger.warning(f"Error: {stderr_data.strip()[:200]}")
                
                return exit_status, stdout_data, stderr_data
                
        except Exception as e:
            logger.error(f"❌ Command execution failed: {e}")
            return 1, "", str(e)
    
    def setup_docker_environment(self):
        """Setup Docker and Elasticsearch using Docker with detailed logging"""
        logger.info("=" * 60)
        logger.info("STEP 2: SETTING UP DOCKER ENVIRONMENT")
        logger.info("=" * 60)
        
        # Check if Docker is already installed
        logger.info("Checking if Docker is already installed...")
        exit_status, stdout, stderr = self.execute_command("docker --version")
        
        if exit_status == 0:
            logger.info(f"✅ Docker already installed: {stdout.strip()}")
        else:
            logger.info("Docker not found, installing Docker...")
            
            setup_commands = [
                ("Updating package list", "apt-get update"),
                ("Installing Docker.io", "apt-get install -y docker.io"),
                ("Starting Docker service", "systemctl start docker"),
                ("Enabling Docker service", "systemctl enable docker"),
                ("Adding user to docker group", f"usermod -aG docker {self.vm_user}"),
            ]
            
            for description, cmd in setup_commands:
                logger.info(f"📦 {description}...")
                exit_status, stdout, stderr = self.execute_command(cmd, use_sudo=True)
                
                if exit_status != 0:
                    logger.warning(f"⚠️ {description} had warnings: {stderr[:100]}")
                else:
                    logger.info(f"✅ {description} completed")
        
        # Check Docker daemon status
        logger.info("Checking Docker daemon status...")
        exit_status, stdout, stderr = self.execute_command("systemctl is-active docker", use_sudo=True)
        if exit_status == 0:
            logger.info(f"✅ Docker daemon is active: {stdout.strip()}")
        else:
            logger.info("Starting Docker daemon...")
            self.execute_command("systemctl start docker", use_sudo=True)
        
        # Pull Elasticsearch image
        logger.info("🐳 Pulling Elasticsearch Docker image...")
        logger.info("This may take a few minutes for first time...")
        exit_status, stdout, stderr = self.execute_command("docker pull elasticsearch:8.15.0")
        
        if exit_status == 0:
            logger.info("✅ Elasticsearch image pulled successfully")
        else:
            logger.warning(f"⚠️ Image pull had issues: {stderr[:200]}")
        
        # Create data directory
        logger.info("📁 Creating Elasticsearch data directory...")
        data_commands = [
            ("Creating data directory", "mkdir -p /opt/elasticsearch-data"),
            ("Setting ownership", f"chown -R {self.vm_user}:{self.vm_user} /opt/elasticsearch-data")
        ]
        
        for description, cmd in data_commands:
            logger.info(f"📁 {description}...")
            exit_status, stdout, stderr = self.execute_command(cmd, use_sudo=True)
            if exit_status == 0:
                logger.info(f"✅ {description} completed")
    
    def create_new_elasticsearch_instance(self, instance_name: str, index_data: dict, schema: dict):
        """Create a new Elasticsearch instance using Docker with comprehensive logging"""
        logger.info("=" * 80)
        logger.info("🚀 STARTING REMOTE ELASTICSEARCH DEPLOYMENT")
        logger.info("=" * 80)
        
        self.instance_name = instance_name
        logger.info(f"Instance name: {instance_name}")
        logger.info(f"Documents to upload: {sum(len(docs) for docs in index_data.values())}")
        
        # Find available port
        logger.info("🔍 Finding available port...")
        available_port = self._find_available_port()
        self.es_port = available_port
        logger.info(f"✅ Selected port: {available_port}")
        
        # Setup Docker environment
        self.setup_docker_environment()
        
        logger.info("=" * 60)
        logger.info("STEP 3: CREATING ELASTICSEARCH CONTAINER")
        logger.info("=" * 60)
        
        # Stop any existing container with same name
        logger.info(f"🧹 Cleaning up existing container: {instance_name}")
        stop_cmd = f"docker stop {instance_name}"
        remove_cmd = f"docker rm {instance_name}"
        
        self.execute_command(stop_cmd)
        self.execute_command(remove_cmd)
        logger.info("✅ Cleanup completed")
        
        # Create and run Elasticsearch container
        docker_run_cmd = f"""docker run -d \
            --name {instance_name} \
            -p {available_port}:9200 \
            -p {available_port + 100}:9300 \
            -e "discovery.type=single-node" \
            -e "xpack.security.enabled=false" \
            -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
            -v /opt/elasticsearch-data/{instance_name}:/usr/share/elasticsearch/data \
            elasticsearch:8.15.0"""
        
        logger.info("🐳 Starting Elasticsearch container...")
        logger.info(f"Container port mapping: {available_port}:9200")
        
        exit_status, stdout, stderr = self.execute_command(docker_run_cmd)
        
        if exit_status != 0:
            logger.error(f"❌ Failed to start container: {stderr}")
            return {'success': False, 'error': f'Container failed to start: {stderr}'}
        
        container_id = stdout.strip()
        logger.info(f"✅ Container started with ID: {container_id[:12]}...")
        
        # Wait for Elasticsearch to start
        logger.info("⏳ Waiting for Elasticsearch to initialize...")
        logger.info("This typically takes 30-60 seconds...")
        
        for i in range(12):  # 60 seconds total
            time.sleep(5)
            logger.info(f"Waiting... ({(i+1)*5}s)")
            
            # Check if container is still running
            check_cmd = f"docker ps | grep {instance_name}"
            exit_status, stdout, stderr = self.execute_command(check_cmd)
            
            if exit_status == 0 and instance_name in stdout:
                logger.info(f"✅ Container is running (attempt {i+1})")
                break
            else:
                logger.warning(f"⚠️ Container check failed (attempt {i+1})")
        else:
            # Check logs for debugging
            logger.error("❌ Container failed to start properly")
            logs_cmd = f"docker logs {instance_name}"
            _, logs, _ = self.execute_command(logs_cmd)
            logger.error(f"Container logs: {logs[:500]}...")
            return {'success': False, 'error': f'Container not running. Check logs: {logs[:200]}'}
        
        # Test Elasticsearch endpoint
        logger.info("🔍 Testing Elasticsearch endpoint...")
        test_cmd = f"curl -s http://localhost:{available_port}/_cluster/health"
        exit_status, health_response, _ = self.execute_command(test_cmd)
        
        if exit_status == 0:
            logger.info(f"✅ Elasticsearch health check passed")
            logger.info(f"Health status: {health_response.strip()[:100]}...")
        else:
            logger.warning("⚠️ Health check failed, but continuing with data upload")
        
        # Upload data
        logger.info("=" * 60)
        logger.info("STEP 4: UPLOADING DATA TO ELASTICSEARCH")
        logger.info("=" * 60)
        
        success = self._upload_data_to_instance(index_data, schema, available_port)
        
        if success:
            access_url = f"http://{self.vm_host}:{available_port}"
            logger.info("=" * 80)
            logger.info("🎉 DEPLOYMENT SUCCESSFUL!")
            logger.info("=" * 80)
            logger.info(f"✅ Elasticsearch instance created at: {access_url}")
            logger.info(f"✅ Container name: {instance_name}")
            logger.info(f"✅ Port: {available_port}")
            logger.info("🌐 Opening browser automatically...")
            
            # Open browser automatically
            try:
                webbrowser.open(access_url)
                logger.info("✅ Browser opened successfully")
            except Exception as e:
                logger.warning(f"⚠️ Failed to open browser: {e}")
            
            return {
                'success': True,
                'host': self.vm_host,
                'port': available_port,
                'instance_name': instance_name,
                'index_name': list(index_data.keys())[0] if index_data else None,
                'access_url': access_url,
                'browser_opened': True,
                'container_id': instance_name
            }
        else:
            logger.error("❌ Data upload failed")
            return {'success': False, 'error': 'Failed to upload data'}
    
    def _find_available_port(self) -> int:
        """Find an available port on the VM with logging"""
        base_port = 9200
        logger.info(f"Checking for available ports starting from {base_port}...")
        
        for port in range(base_port, base_port + 100):
            exit_status, stdout, stderr = self.execute_command(f"netstat -tuln | grep :{port}")
            if exit_status != 0 or not stdout.strip():
                logger.info(f"✅ Port {port} is available")
                return port
            else:
                logger.info(f"Port {port} is in use")
        
        logger.warning(f"Using fallback port 9300")
        return 9300  # Fallback port
    
    def _upload_data_to_instance(self, index_data: dict, schema: dict, port: int) -> bool:
        """Upload data to the new Elasticsearch instance with detailed logging"""
        try:
            # Connect to the new Elasticsearch instance
            es_url = f"http://{self.vm_host}:{port}"
            logger.info(f"📡 Connecting to Elasticsearch at: {es_url}")
            
            es_client = Elasticsearch([es_url], verify_certs=False, timeout=60)
            
            # Wait for ES to be ready with multiple attempts
            logger.info("⏳ Waiting for Elasticsearch to accept connections...")
            
            for i in range(30):
                try:
                    if es_client.ping():
                        logger.info(f"✅ Elasticsearch is ready! (attempt {i+1})")
                        
                        # Get cluster info
                        try:
                            info = es_client.info()
                            logger.info(f"Cluster name: {info.get('cluster_name', 'unknown')}")
                            logger.info(f"ES version: {info.get('version', {}).get('number', 'unknown')}")
                        except:
                            pass
                        
                        break
                except Exception as e:
                    logger.info(f"Connection attempt {i+1}/30 failed: {str(e)[:50]}...")
                    time.sleep(5)
            else:
                logger.error("❌ Elasticsearch failed to become ready after 150 seconds")
                return False
            
            # Create indices and upload data
            total_uploaded = 0
            for index_name, documents in index_data.items():
                logger.info(f"📊 Processing index: {index_name}")
                logger.info(f"📊 Documents to upload: {len(documents)}")
                
                # Create index with schema
                try:
                    logger.info("🏗️ Creating index with schema...")
                    es_client.indices.create(index=index_name, body=schema, ignore=400)
                    logger.info("✅ Index created successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Index creation warning: {str(e)[:100]}...")
                
                # Bulk upload documents
                logger.info("📤 Starting bulk document upload...")
                from elasticsearch.helpers import bulk
                
                actions = []
                for i, doc in enumerate(documents):
                    actions.append({
                        '_index': index_name,
                        '_id': f"{index_name}_{i}",
                        '_source': doc
                    })
                
                # Upload in batches
                batch_size = 100
                batches_total = (len(actions) + batch_size - 1) // batch_size
                logger.info(f"📦 Uploading {batches_total} batches of {batch_size} documents each")
                
                for i in range(0, len(actions), batch_size):
                    batch_num = i // batch_size + 1
                    batch = actions[i:i+batch_size]
                    
                    try:
                        success, failed = bulk(es_client, batch, chunk_size=batch_size, request_timeout=60)
                        total_uploaded += success
                        logger.info(f"✅ Batch {batch_num}/{batches_total}: {success} documents uploaded")
                        
                        if failed:
                            logger.warning(f"⚠️ Batch {batch_num}: {len(failed)} documents failed")
                            
                    except Exception as e:
                        logger.warning(f"❌ Batch {batch_num} upload failed: {str(e)[:100]}...")
                
                logger.info(f"✅ Total uploaded to {index_name}: {total_uploaded} documents")
                
                # Refresh index
                logger.info("🔄 Refreshing index to make documents searchable...")
                es_client.indices.refresh(index=index_name)
                logger.info("✅ Index refreshed")
                
                # Verify document count
                try:
                    count_result = es_client.count(index=index_name)
                    actual_count = count_result['count']
                    logger.info(f"✅ Verification: {actual_count} documents are searchable")
                except Exception as e:
                    logger.warning(f"⚠️ Could not verify document count: {e}")
            
            logger.info(f"🎉 All data uploaded successfully! Total documents: {total_uploaded}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data upload failed: {e}")
            return False

class RemoteElasticsearchManager:
    """Manage Elasticsearch deployment on remote VM with Docker"""
    
    def __init__(self, vm_host="54.227.251.28", vm_user="khemchand", vm_password="wq0XYdUWKa1EN7LI7"):
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.vm_password = vm_password
        self.ssh_client = None
        self.es_port = 9200
        self.instance_name = None
        
    def connect_ssh(self):
        """Establish SSH connection to VM"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh_client.connect(
                hostname=self.vm_host,
                username=self.vm_user,
                password=self.vm_password,
                timeout=30,
                auth_timeout=30,
                banner_timeout=30
            )
            logger.info(f"Successfully connected to {self.vm_host}")
            return True
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            return False
    
    def disconnect_ssh(self):
        """Close SSH connection"""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def execute_command(self, command: str, use_sudo=False) -> tuple:
        """Execute command on remote VM with improved sudo handling"""
        try:
            if use_sudo and not command.startswith('sudo'):
                command = f"sudo {command}"
            
            if use_sudo and command.startswith('sudo'):
                # Use expect-like approach for sudo commands
                full_command = f"echo '{self.vm_password}' | sudo -S {command[5:]}"
                stdin, stdout, stderr = self.ssh_client.exec_command(full_command)
                exit_status = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                return exit_status, stdout_data, stderr_data
            else:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                return exit_status, stdout_data, stderr_data
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return 1, "", str(e)
    
    def setup_docker_environment(self):
        """Setup Docker and Elasticsearch using Docker"""
        logger.info("Setting up Docker environment...")
        
        commands = [
            # Update system
            "apt-get update",
            
            # Install Docker if not present
            "apt-get install -y docker.io",
            "systemctl start docker",
            "systemctl enable docker",
            
            # Add user to docker group
            f"usermod -aG docker {self.vm_user}",
            
            # Pull Elasticsearch Docker image
            "docker pull elasticsearch:8.15.0",
            
            # Create directory for elasticsearch data
            "mkdir -p /opt/elasticsearch-data",
            f"chown -R {self.vm_user}:{self.vm_user} /opt/elasticsearch-data"
        ]
        
        for cmd in commands:
            logger.info(f"Executing: {cmd}")
            exit_status, stdout, stderr = self.execute_command(cmd, use_sudo=True)
            if exit_status != 0:
                logger.warning(f"Command warning: {cmd}, Error: {stderr}")
            else:
                logger.info(f"Command successful: {cmd}")
    
    def create_new_elasticsearch_instance(self, instance_name: str, index_data: dict, schema: dict):
        """Create a new Elasticsearch instance using Docker"""
        self.instance_name = instance_name
        
        logger.info(f"Creating new Elasticsearch Docker instance: {instance_name}")
        
        # Find available port
        available_port = self._find_available_port()
        self.es_port = available_port
        
        # Setup Docker environment
        self.setup_docker_environment()
        
        # Stop any existing container with same name
        stop_cmd = f"docker stop {instance_name} || true"
        remove_cmd = f"docker rm {instance_name} || true"
        self.execute_command(stop_cmd)
        self.execute_command(remove_cmd)
        
        # Create and run Elasticsearch container
        docker_run_cmd = f"""docker run -d \
            --name {instance_name} \
            -p {available_port}:9200 \
            -p {available_port + 100}:9300 \
            -e "discovery.type=single-node" \
            -e "xpack.security.enabled=false" \
            -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
            -v /opt/elasticsearch-data/{instance_name}:/usr/share/elasticsearch/data \
            elasticsearch:8.15.0"""
        
        logger.info(f"Starting Elasticsearch container on port {available_port}")
        exit_status, stdout, stderr = self.execute_command(docker_run_cmd)
        
        if exit_status != 0:
            logger.error(f"Failed to start container: {stderr}")
            return {'success': False, 'error': f'Container failed to start: {stderr}'}
        
        # Wait for Elasticsearch to start
        logger.info("Waiting for Elasticsearch to start...")
        time.sleep(60)  # Give more time for ES to start
        
        # Verify container is running
        check_cmd = f"docker ps | grep {instance_name}"
        exit_status, stdout, stderr = self.execute_command(check_cmd)
        
        if exit_status == 0 and instance_name in stdout:
            logger.info(f"Elasticsearch container {instance_name} is running")
        else:
            # Check logs for debugging
            logs_cmd = f"docker logs {instance_name}"
            _, logs, _ = self.execute_command(logs_cmd)
            logger.error(f"Container not running. Logs: {logs}")
            return {'success': False, 'error': f'Container not running. Logs: {logs[:500]}'}
        
        # Test Elasticsearch endpoint
        test_cmd = f"curl -s http://localhost:{available_port}/_cluster/health"
        exit_status, health_response, _ = self.execute_command(test_cmd)
        
        if exit_status == 0:
            logger.info(f"Elasticsearch health check passed: {health_response}")
        else:
            logger.warning("Health check failed, but continuing with data upload")
        
        # Create index and upload data
        success = self._upload_data_to_instance(index_data, schema, available_port)
        
        if success:
            access_url = f"http://{self.vm_host}:{available_port}"
            logger.info(f"Successfully created Elasticsearch instance at {access_url}")
            
            # Open browser automatically
            try:
                logger.info(f"Opening browser to {access_url}")
                webbrowser.open(access_url)
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")
            
            return {
                'success': True,
                'host': self.vm_host,
                'port': available_port,
                'instance_name': instance_name,
                'index_name': list(index_data.keys())[0] if index_data else None,
                'access_url': access_url,
                'browser_opened': True,
                'container_id': instance_name
            }
        else:
            return {'success': False, 'error': 'Failed to upload data'}
    
    def _find_available_port(self) -> int:
        """Find an available port on the VM"""
        base_port = 9200
        for port in range(base_port, base_port + 100):
            exit_status, stdout, stderr = self.execute_command(f"netstat -tuln | grep :{port}")
            if exit_status != 0 or not stdout.strip():
                return port
        return 9300  # Fallback port
    
    def _upload_data_to_instance(self, index_data: dict, schema: dict, port: int) -> bool:
        """Upload data to the new Elasticsearch instance"""
        try:
            # Connect to the new Elasticsearch instance
            es_url = f"http://{self.vm_host}:{port}"
            es_client = Elasticsearch([es_url], verify_certs=False, timeout=60)
            
            # Wait for ES to be ready with multiple attempts
            logger.info("Waiting for Elasticsearch to be ready for data upload...")
            for i in range(30):
                try:
                    if es_client.ping():
                        logger.info(f"Elasticsearch is ready on attempt {i+1}")
                        break
                except Exception as e:
                    logger.info(f"Waiting for ES to be ready, attempt {i+1}/30: {e}")
                    time.sleep(5)
            else:
                logger.error("Elasticsearch failed to become ready")
                return False
            
            # Create indices and upload data
            for index_name, documents in index_data.items():
                logger.info(f"Creating index {index_name} with {len(documents)} documents")
                
                # Create index with schema
                try:
                    es_client.indices.create(index=index_name, body=schema, ignore=400)
                    logger.info(f"Index {index_name} created successfully")
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
                
                # Bulk upload documents
                from elasticsearch.helpers import bulk
                
                actions = []
                for i, doc in enumerate(documents):
                    actions.append({
                        '_index': index_name,
                        '_id': f"{index_name}_{i}",
                        '_source': doc
                    })
                
                # Upload in smaller batches
                batch_size = 100
                total_uploaded = 0
                for i in range(0, len(actions), batch_size):
                    batch = actions[i:i+batch_size]
                    try:
                        success, failed = bulk(es_client, batch, chunk_size=batch_size, request_timeout=60)
                        total_uploaded += success
                        logger.info(f"Uploaded batch {i//batch_size + 1}, {success} documents")
                    except Exception as e:
                        logger.warning(f"Batch upload failed: {e}")
                
                logger.info(f"Successfully uploaded {total_uploaded} documents to {index_name}")
                
                # Refresh index
                es_client.indices.refresh(index=index_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Data upload failed: {e}")
            return False
    
    def list_instances(self) -> list:
        """List all Elasticsearch Docker containers"""
        try:
            exit_status, stdout, stderr = self.execute_command("docker ps --filter ancestor=elasticsearch:8.15.0 --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'")
            
            instances = []
            lines = stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        name = parts[0].strip()
                        ports = parts[1].strip()
                        status = parts[2].strip()
                        
                        # Extract port from ports string
                        port = 9200
                        if '->' in ports:
                            try:
                                port = int(ports.split('->')[0].split(':')[-1])
                            except:
                                pass
                        
                        instances.append({
                            'name': name,
                            'port': port,
                            'status': 'running' if 'Up' in status else 'stopped',
                            'url': f"http://{self.vm_host}:{port}"
                        })
            
            return instances
            
        except Exception as e:
            logger.error(f"Failed to list instances: {e}")
            return []
    
    def stop_instance(self, instance_name: str) -> bool:
        """Stop an Elasticsearch Docker container"""
        try:
            exit_status, stdout, stderr = self.execute_command(f"docker stop {instance_name}")
            return exit_status == 0
        except Exception as e:
            logger.error(f"Failed to stop instance {instance_name}: {e}")
            return False
    
    def delete_instance(self, instance_name: str) -> bool:
        """Delete an Elasticsearch Docker container completely"""
        try:
            # Stop and remove container
            self.execute_command(f"docker stop {instance_name}")
            exit_status, stdout, stderr = self.execute_command(f"docker rm {instance_name}")
            
            # Remove data directory
            self.execute_command(f"rm -rf /opt/elasticsearch-data/{instance_name}", use_sudo=True)
            
            logger.info(f"Successfully deleted instance: {instance_name}")
            return exit_status == 0
            
        except Exception as e:
            logger.error(f"Failed to delete instance {instance_name}: {e}")
            return False
    
    def get_instance_info(self, instance_name: str) -> dict:
        """Get detailed information about a Docker container instance"""
        try:
            # Check if container is running
            exit_status, stdout, stderr = self.execute_command(f"docker ps | grep {instance_name}")
            
            if exit_status == 0 and instance_name in stdout:
                # Extract port from docker ps output
                port = 9200
                if '->' in stdout:
                    try:
                        port = int(stdout.split('->')[0].split(':')[-1])
                    except:
                        pass
                
                # Get indices information
                try:
                    es_client = Elasticsearch([f"http://{self.vm_host}:{port}"], verify_certs=False)
                    indices = es_client.cat.indices(format='json')
                    
                    return {
                        'name': instance_name,
                        'status': 'running',
                        'port': port,
                        'url': f"http://{self.vm_host}:{port}",
                        'indices': [idx['index'] for idx in indices],
                        'total_docs': sum(int(idx.get('docs.count', 0)) for idx in indices)
                    }
                except:
                    return {
                        'name': instance_name,
                        'status': 'running',
                        'port': port,
                        'url': f"http://{self.vm_host}:{port}",
                        'indices': [],
                        'total_docs': 0
                    }
            else:
                return {
                    'name': instance_name,
                    'status': 'stopped',
                    'error': 'Container not running'
                }
                
        except Exception as e:
            logger.error(f"Failed to get instance info: {e}")
            return {
                'name': instance_name,
                'status': 'error',
                'error': str(e)
            }
if __name__ == '__main__':
    print("Simple Elasticsearch Uploader")
    print("Visit: http://localhost:5000")
    print("- Upload CSV or JSON")
    print("- Choose local or remote deployment") 
    print("- Browser opens automatically")
    app.run(host='0.0.0.0', port=5000, debug=False)
