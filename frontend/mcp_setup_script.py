# minimal_mcp_integration.py - Remote MCP integration without heavy dependencies
import os
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

# Try to import the remote MCP server
try:
    from remote_mcp_elasticsearch_server import remote_mcp_server, auto_connect_remote_mcp
    REMOTE_MCP_AVAILABLE = True
    logger.info("Remote MCP integration available")
except ImportError:
    REMOTE_MCP_AVAILABLE = False
    logger.info("Remote MCP integration not available")

class SimpleRemoteMCPIntegration:
    """
    Simple remote MCP integration that deploys on the same server as Elasticsearch
    """
    def __init__(self, base_dir="mcp_configs"):
        self.base_dir = base_dir
        self.connections = {}
        os.makedirs(base_dir, exist_ok=True)
        self.remote_host = "54.227.251.28"  # Same as your ES server
    
    def auto_setup_mcp(self, es_instance_info):
        """Setup MCP server on remote host"""
        if not REMOTE_MCP_AVAILABLE:
            # Fallback to simple config creation
            return self._create_simple_config(es_instance_info)
        
        # Use the full remote MCP deployment
        try:
            # Run the async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(auto_connect_remote_mcp(es_instance_info))
            finally:
                loop.close()
            
            return result
        except Exception as e:
            logger.error(f"Remote MCP deployment failed: {e}")
            return self._create_simple_config(es_instance_info)
    
    def _create_simple_config(self, es_instance_info):
        """Fallback: create simple config file"""
        instance_name = es_instance_info.get('instance_name', 'unknown')
        config_file = os.path.join(self.base_dir, f"{instance_name}-config.json")
        
        config = {
            "name": f"mcp-{instance_name}",
            "elasticsearch_url": es_instance_info.get('access_url', 'http://localhost:9200'),
            "remote_host": self.remote_host,
            "port": 8080 + len(self.connections),
            "deployment": "remote_ssh",
            "created_at": "auto-generated",
            "note": "Remote MCP server configuration"
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.connections[instance_name] = config
            
            return {
                'success': True,
                'config_file': config_file,
                'message': f'Remote MCP config created for {instance_name}',
                'remote_host': self.remote_host,
                'mcp_url': f'http://{self.remote_host}:{config["port"]}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_connections(self):
        """Get all MCP connections"""
        if REMOTE_MCP_AVAILABLE:
            return remote_mcp_server.get_active_connections()
        else:
            return {
                'connections': self.connections,
                'total_count': len(self.connections),
                'deployment_type': 'remote_ssh_simple'
            }

# Global instance
simple_remote_mcp = SimpleRemoteMCPIntegration()

def add_mcp_to_deployment_result(result):
    """Add remote MCP setup to deployment result"""
    if result.get('success'):
        try:
            mcp_result = simple_remote_mcp.auto_setup_mcp(result)
            result['mcp_integration'] = mcp_result
            
            if mcp_result['success']:
                logger.info(f"Remote MCP integration added for {result.get('instance_name')}")
                if 'mcp_url' in mcp_result:
                    logger.info(f"Remote MCP URL: {mcp_result['mcp_url']}")
        except Exception as e:
            logger.error(f"MCP integration failed: {e}")
            result['mcp_integration'] = {
                'success': False,
                'error': str(e),
                'deployment_type': 'remote_ssh'
            }
    
    return result
