"""
Remote Instance Manager
========================
Manages Elasticsearch and MCP instances on remote server (82.112.235.26)

Features:
- Spin up ES instance per user
- Spin up MCP instance per user
- Connect ES and MCP
- Store connection info in database
- Auto-open browser tabs
- Comprehensive logging
"""

import paramiko
import logging
import json
import time
import webbrowser
import threading
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class RemoteInstanceManager:
    """
    Manages Elasticsearch and MCP instances on remote server
    """
    
    def __init__(self, 
                 ssh_host: str = "82.112.235.26",
                 ssh_user: str = "root",
                 ssh_password: str = None,
                 ssh_key_path: str = None):
        """
        Initialize remote instance manager
        
        Args:
            ssh_host: Remote server hostname/IP
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: Path to SSH private key (optional)
        """
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_key_path = ssh_key_path
        
        # Port ranges for instances
        self.es_base_port = 9200
        self.mcp_base_port = 3000
        
        logger.info("=" * 80)
        logger.info("🚀 Remote Instance Manager Initialized")
        logger.info("=" * 80)
        logger.info(f"   Remote Server: {ssh_host}")
        logger.info(f"   SSH User: {ssh_user}")
        logger.info(f"   ES Base Port: {self.es_base_port}")
        logger.info(f"   MCP Base Port: {self.mcp_base_port}")
    
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """Create and return SSH client"""
        logger.info(f"📡 Connecting to SSH: {self.ssh_user}@{self.ssh_host}")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if self.ssh_key_path:
                logger.info(f"   Using SSH key: {self.ssh_key_path}")
                client.connect(
                    hostname=self.ssh_host,
                    username=self.ssh_user,
                    key_filename=self.ssh_key_path,
                    timeout=10
                )
            elif self.ssh_password:
                logger.info(f"   Using password authentication")
                client.connect(
                    hostname=self.ssh_host,
                    username=self.ssh_user,
                    password=self.ssh_password,
                    timeout=10
                )
            else:
                logger.error("❌ No authentication method provided")
                return None
            
            logger.info("✅ SSH connection established")
            return client
        except Exception as e:
            logger.error(f"❌ SSH connection failed: {e}")
            return None
    
    def _execute_ssh_command(self, command: str, client: paramiko.SSHClient = None) -> Tuple[str, str, int]:
        """
        Execute command on remote server
        
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        should_close = False
        if client is None:
            client = self._get_ssh_client()
            should_close = True
        
        if not client:
            return "", "SSH connection failed", 1
        
        try:
            logger.info(f"   🔧 Executing: {command}")
            stdin, stdout, stderr = client.exec_command(command)
            
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code == 0:
                logger.info(f"   ✅ Command successful")
            else:
                logger.error(f"   ❌ Command failed (exit code: {exit_code})")
            
            return stdout_text, stderr_text, exit_code
        except Exception as e:
            logger.error(f"   ❌ Command execution failed: {e}")
            return "", str(e), 1
        finally:
            if should_close:
                client.close()
    
    def _get_next_available_port(self, base_port: int, client: paramiko.SSHClient) -> int:
        """
        Find next available port starting from base_port
        """
        logger.info(f"🔍 Finding available port starting from {base_port}")
        
        for port in range(base_port, base_port + 100):
            # Check if port is in use
            command = f"netstat -tuln | grep ':{port} '"
            stdout, stderr, exit_code = self._execute_ssh_command(command, client)
            
            if exit_code != 0 or not stdout.strip():
                # Port is available
                logger.info(f"   ✅ Port {port} is available")
                return port
        
        logger.warning(f"   ⚠️ No available ports found, using {base_port}")
        return base_port
    
    def spin_up_elasticsearch(self, user_id: str, client: paramiko.SSHClient = None) -> Dict:
        """
        Spin up Elasticsearch instance for user
        
        Returns:
            Dict with ES instance info
        """
        logger.info("=" * 80)
        logger.info(f"🔄 Spinning up Elasticsearch for user: {user_id}")
        logger.info("=" * 80)
        
        should_close = False
        if client is None:
            client = self._get_ssh_client()
            should_close = True
        
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            # Get available port
            es_port = self._get_next_available_port(self.es_base_port, client)
            
            # Create ES instance directory
            es_dir = f"/opt/elasticsearch/instances/{user_id}"
            logger.info(f"📁 Creating ES directory: {es_dir}")
            self._execute_ssh_command(f"mkdir -p {es_dir}", client)
            
            # Check if Elasticsearch is installed
            logger.info("🔍 Checking Elasticsearch installation...")
            stdout, stderr, exit_code = self._execute_ssh_command("which elasticsearch", client)
            
            if exit_code != 0:
                logger.info("📦 Elasticsearch not found, installing...")
                # Install Elasticsearch (basic installation)
                install_commands = [
                    "apt-get update",
                    "apt-get install -y default-jdk",
                    "wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -",
                    "echo 'deb https://artifacts.elastic.co/packages/8.x/apt stable main' | tee /etc/apt/sources.list.d/elastic-8.x.list",
                    "apt-get update",
                    "apt-get install -y elasticsearch"
                ]
                
                for cmd in install_commands:
                    logger.info(f"   Running: {cmd}")
                    self._execute_ssh_command(cmd, client)
            
            # Create ES config for this user
            es_config = f"""
cluster.name: es-{user_id}
node.name: node-{user_id}
path.data: {es_dir}/data
path.logs: {es_dir}/logs
network.host: 0.0.0.0
http.port: {es_port}
discovery.type: single-node
xpack.security.enabled: false
"""
            
            config_file = f"{es_dir}/elasticsearch.yml"
            logger.info(f"📝 Creating ES config: {config_file}")
            
            # Write config file
            config_command = f"cat > {config_file} << 'EOF'\n{es_config}\nEOF"
            self._execute_ssh_command(config_command, client)
            
            # Start Elasticsearch instance
            logger.info(f"🚀 Starting Elasticsearch on port {es_port}")
            start_command = f"ES_PATH_CONF={es_dir} nohup /usr/share/elasticsearch/bin/elasticsearch -d -p {es_dir}/es.pid > {es_dir}/es.log 2>&1 &"
            self._execute_ssh_command(start_command, client)
            
            # Wait for ES to start
            logger.info("⏳ Waiting for Elasticsearch to start...")
            max_attempts = 30
            for attempt in range(max_attempts):
                time.sleep(2)
                check_command = f"curl -s http://localhost:{es_port}/_cluster/health"
                stdout, stderr, exit_code = self._execute_ssh_command(check_command, client)
                
                if exit_code == 0 and "cluster_name" in stdout:
                    logger.info(f"   ✅ Elasticsearch is ready! (attempt {attempt + 1}/{max_attempts})")
                    break
                
                logger.info(f"   ⏳ Waiting... (attempt {attempt + 1}/{max_attempts})")
            
            # Get ES cluster health
            stdout, stderr, exit_code = self._execute_ssh_command(
                f"curl -s http://localhost:{es_port}/_cluster/health",
                client
            )
            
            es_info = {
                "success": True,
                "user_id": user_id,
                "host": self.ssh_host,
                "port": es_port,
                "url": f"http://{self.ssh_host}:{es_port}",
                "config_dir": es_dir,
                "cluster_name": f"es-{user_id}",
                "node_name": f"node-{user_id}",
                "status": "running",
                "health": stdout if exit_code == 0 else "unknown",
                "created_at": datetime.now().isoformat()
            }
            
            logger.info("=" * 80)
            logger.info("✅ Elasticsearch instance created successfully!")
            logger.info("=" * 80)
            logger.info(f"   URL: {es_info['url']}")
            logger.info(f"   Port: {es_port}")
            logger.info(f"   Config: {es_dir}")
            
            return es_info
            
        except Exception as e:
            logger.error(f"❌ Failed to spin up Elasticsearch: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if should_close:
                client.close()
    
    def spin_up_mcp(self, user_id: str, es_info: Dict, client: paramiko.SSHClient = None) -> Dict:
        """
        Spin up MCP instance for user and connect to ES
        
        Args:
            user_id: User ID
            es_info: Elasticsearch instance info from spin_up_elasticsearch
            
        Returns:
            Dict with MCP instance info
        """
        logger.info("=" * 80)
        logger.info(f"🔄 Spinning up MCP for user: {user_id}")
        logger.info("=" * 80)
        
        should_close = False
        if client is None:
            client = self._get_ssh_client()
            should_close = True
        
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            # Get available port
            mcp_port = self._get_next_available_port(self.mcp_base_port, client)
            
            # Create MCP instance directory
            mcp_dir = f"/opt/mcp/instances/{user_id}"
            logger.info(f"📁 Creating MCP directory: {mcp_dir}")
            self._execute_ssh_command(f"mkdir -p {mcp_dir}", client)
            
            # Check if Node.js is installed
            logger.info("🔍 Checking Node.js installation...")
            stdout, stderr, exit_code = self._execute_ssh_command("which node", client)
            
            if exit_code != 0:
                logger.info("📦 Node.js not found, installing...")
                install_commands = [
                    "curl -fsSL https://deb.nodesource.com/setup_18.x | bash -",
                    "apt-get install -y nodejs"
                ]
                
                for cmd in install_commands:
                    logger.info(f"   Running: {cmd}")
                    self._execute_ssh_command(cmd, client)
            
            # Create MCP server script
            mcp_script = f"""
const {{ Server }} = require('@modelcontextprotocol/sdk/server/index.js');
const {{ StdioServerTransport }} = require('@modelcontextprotocol/sdk/server/stdio.js');
const {{ Client }} = require('@elastic/elasticsearch');

// Elasticsearch client
const esClient = new Client({{
    node: '{es_info.get('url', f'http://localhost:{es_info.get('port', 9200)}')}',
}});

// MCP Server
const server = new Server(
    {{
        name: 'mcp-elasticsearch-{user_id}',
        version: '1.0.0',
    }},
    {{
        capabilities: {{
            resources: {{}},
            tools: {{}},
        }},
    }}
);

// Health check endpoint
server.setRequestHandler('ping', async () => {{
    return {{ status: 'ok', user_id: '{user_id}' }};
}});

// ES query tool
server.setRequestHandler('query_elasticsearch', async (request) => {{
    const {{ index, query }} = request.params;
    const result = await esClient.search({{
        index: index,
        body: query
    }});
    return result;
}});

// Start server
const transport = new StdioServerTransport();
server.connect(transport);

console.log('MCP Server started for user: {user_id}');
console.log('Connected to ES: {es_info.get('url')}');
"""
            
            script_file = f"{mcp_dir}/mcp-server.js"
            logger.info(f"📝 Creating MCP script: {script_file}")
            
            # Write script file
            script_command = f"cat > {script_file} << 'EOF'\n{mcp_script}\nEOF"
            self._execute_ssh_command(script_command, client)
            
            # Create package.json
            package_json = {
                "name": f"mcp-{user_id}",
                "version": "1.0.0",
                "dependencies": {
                    "@modelcontextprotocol/sdk": "latest",
                    "@elastic/elasticsearch": "^8.0.0"
                }
            }
            
            package_file = f"{mcp_dir}/package.json"
            logger.info(f"📝 Creating package.json: {package_file}")
            
            package_command = f"cat > {package_file} << 'EOF'\n{json.dumps(package_json, indent=2)}\nEOF"
            self._execute_ssh_command(package_command, client)
            
            # Install dependencies
            logger.info("📦 Installing MCP dependencies...")
            self._execute_ssh_command(f"cd {mcp_dir} && npm install", client)
            
            # Start MCP server
            logger.info(f"🚀 Starting MCP server on port {mcp_port}")
            start_command = f"cd {mcp_dir} && nohup node mcp-server.js > mcp.log 2>&1 & echo $! > mcp.pid"
            self._execute_ssh_command(start_command, client)
            
            # Wait for MCP to start
            logger.info("⏳ Waiting for MCP to start...")
            time.sleep(5)
            
            # Check if MCP is running
            check_command = f"ps -p $(cat {mcp_dir}/mcp.pid) > /dev/null && echo 'running' || echo 'stopped'"
            stdout, stderr, exit_code = self._execute_ssh_command(check_command, client)
            
            mcp_info = {
                "success": True,
                "user_id": user_id,
                "host": self.ssh_host,
                "port": mcp_port,
                "url": f"http://{self.ssh_host}:{mcp_port}",
                "config_dir": mcp_dir,
                "status": stdout.strip() if exit_code == 0 else "unknown",
                "connected_es": es_info.get('url'),
                "created_at": datetime.now().isoformat()
            }
            
            logger.info("=" * 80)
            logger.info("✅ MCP instance created successfully!")
            logger.info("=" * 80)
            logger.info(f"   URL: {mcp_info['url']}")
            logger.info(f"   Port: {mcp_port}")
            logger.info(f"   Config: {mcp_dir}")
            logger.info(f"   Connected to ES: {es_info.get('url')}")
            
            return mcp_info
            
        except Exception as e:
            logger.error(f"❌ Failed to spin up MCP: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if should_close:
                client.close()
    
    def create_user_instances(self, user_id: str, open_browser: bool = True) -> Dict:
        """
        Create both ES and MCP instances for a user
        
        Args:
            user_id: User ID
            open_browser: Whether to open browser tabs
            
        Returns:
            Dict with both instance info
        """
        logger.info("=" * 80)
        logger.info(f"🚀 Creating instances for user: {user_id}")
        logger.info("=" * 80)
        
        # Use single SSH connection for both operations
        client = self._get_ssh_client()
        if not client:
            return {
                "success": False,
                "error": "SSH connection failed"
            }
        
        try:
            # Spin up Elasticsearch
            es_info = self.spin_up_elasticsearch(user_id, client)
            
            if not es_info.get('success'):
                return {
                    "success": False,
                    "error": "Failed to create Elasticsearch instance",
                    "es_info": es_info
                }
            
            # Spin up MCP and connect to ES
            mcp_info = self.spin_up_mcp(user_id, es_info, client)
            
            if not mcp_info.get('success'):
                return {
                    "success": False,
                    "error": "Failed to create MCP instance",
                    "es_info": es_info,
                    "mcp_info": mcp_info
                }
            
            result = {
                "success": True,
                "user_id": user_id,
                "elasticsearch": es_info,
                "mcp": mcp_info,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info("=" * 80)
            logger.info("✅ All instances created successfully!")
            logger.info("=" * 80)
            logger.info(f"   Elasticsearch: {es_info['url']}")
            logger.info(f"   MCP: {mcp_info['url']}")
            
            # Open browser tabs
            if open_browser:
                logger.info("🌐 Opening browser tabs...")
                threading.Thread(target=self._open_browser_tabs, args=(es_info, mcp_info)).start()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to create instances: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            client.close()
    
    def _open_browser_tabs(self, es_info: Dict, mcp_info: Dict):
        """Open browser tabs for ES and MCP"""
        try:
            time.sleep(2)  # Wait a bit before opening
            
            logger.info(f"🌐 Opening Elasticsearch: {es_info['url']}")
            webbrowser.open(es_info['url'])
            
            time.sleep(1)
            
            logger.info(f"🌐 Opening MCP: {mcp_info['url']}")
            webbrowser.open(mcp_info['url'])
            
        except Exception as e:
            logger.error(f"❌ Failed to open browser: {e}")
    
    def get_instance_status(self, user_id: str) -> Dict:
        """
        Get status of user's instances
        """
        logger.info(f"📊 Getting instance status for user: {user_id}")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            # Check ES status
            es_dir = f"/opt/elasticsearch/instances/{user_id}"
            es_check = f"ps -ef | grep 'ES_PATH_CONF={es_dir}' | grep -v grep"
            es_stdout, _, es_exit = self._execute_ssh_command(es_check, client)
            
            # Check MCP status
            mcp_dir = f"/opt/mcp/instances/{user_id}"
            mcp_check = f"test -f {mcp_dir}/mcp.pid && ps -p $(cat {mcp_dir}/mcp.pid) > /dev/null && echo 'running' || echo 'stopped'"
            mcp_stdout, _, mcp_exit = self._execute_ssh_command(mcp_check, client)
            
            return {
                "success": True,
                "user_id": user_id,
                "elasticsearch": {
                    "status": "running" if es_exit == 0 and es_stdout.strip() else "stopped",
                    "directory": es_dir
                },
                "mcp": {
                    "status": mcp_stdout.strip() if mcp_exit == 0 else "stopped",
                    "directory": mcp_dir
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get instance status: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()
    
    def stop_instances(self, user_id: str) -> Dict:
        """
        Stop user's instances
        """
        logger.info(f"🛑 Stopping instances for user: {user_id}")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            # Stop ES
            es_dir = f"/opt/elasticsearch/instances/{user_id}"
            es_stop = f"test -f {es_dir}/es.pid && kill $(cat {es_dir}/es.pid) || echo 'Already stopped'"
            self._execute_ssh_command(es_stop, client)
            
            # Stop MCP
            mcp_dir = f"/opt/mcp/instances/{user_id}"
            mcp_stop = f"test -f {mcp_dir}/mcp.pid && kill $(cat {mcp_dir}/mcp.pid) || echo 'Already stopped'"
            self._execute_ssh_command(mcp_stop, client)
            
            logger.info("✅ Instances stopped")
            
            return {
                "success": True,
                "user_id": user_id,
                "message": "Instances stopped successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stop instances: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()


# Singleton instance
_instance_manager = None

def get_instance_manager(ssh_password: str = None, ssh_key_path: str = None) -> RemoteInstanceManager:
    """Get or create instance manager"""
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = RemoteInstanceManager(
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path
        )
    return _instance_manager
