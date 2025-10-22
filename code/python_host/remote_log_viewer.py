"""
Remote Server Log Viewer
=========================
View logs from 82.112.235.26 in real-time

Features:
- SSH to remote server
- Tail logs in real-time
- View ES instance logs
- View MCP instance logs
- Stream to browser
"""

import paramiko
import logging
import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class RemoteLogViewer:
    """
    View logs from remote server in real-time
    """
    
    def __init__(self, 
                 ssh_host: str = "82.112.235.26",
                 ssh_user: str = "root",
                 ssh_password: str = None,
                 ssh_key_path: str = None):
        """
        Initialize remote log viewer
        """
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_key_path = ssh_key_path
        
        # Log streams
        self.log_streams = {}
        self.active_streams = {}
        
        logger.info("🔍 Remote Log Viewer initialized")
        logger.info(f"   Server: {ssh_host}")
    
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """Create and return SSH client"""
        logger.info(f"📡 Connecting to SSH: {self.ssh_user}@{self.ssh_host}")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if self.ssh_key_path:
                client.connect(
                    hostname=self.ssh_host,
                    username=self.ssh_user,
                    key_filename=self.ssh_key_path,
                    timeout=10
                )
            elif self.ssh_password:
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
    
    def get_es_logs(self, user_id: str, lines: int = 100) -> Dict:
        """
        Get Elasticsearch logs for a user
        
        Args:
            user_id: User ID
            lines: Number of lines to retrieve
            
        Returns:
            Dict with logs
        """
        logger.info(f"📋 Getting ES logs for user: {user_id} (last {lines} lines)")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            log_file = f"/opt/elasticsearch/instances/{user_id}/es.log"
            
            # Check if log file exists
            check_cmd = f"test -f {log_file} && echo 'exists' || echo 'not found'"
            stdin, stdout, stderr = client.exec_command(check_cmd)
            result = stdout.read().decode('utf-8').strip()
            
            if result != 'exists':
                return {
                    "success": False,
                    "error": f"Log file not found: {log_file}",
                    "user_id": user_id
                }
            
            # Get last N lines
            cmd = f"tail -n {lines} {log_file}"
            stdin, stdout, stderr = client.exec_command(cmd)
            
            logs = stdout.read().decode('utf-8')
            
            logger.info(f"✅ Retrieved {len(logs.splitlines())} log lines")
            
            return {
                "success": True,
                "user_id": user_id,
                "log_file": log_file,
                "lines": logs.splitlines(),
                "total_lines": len(logs.splitlines())
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get ES logs: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()
    
    def get_mcp_logs(self, user_id: str, lines: int = 100) -> Dict:
        """
        Get MCP logs for a user
        
        Args:
            user_id: User ID
            lines: Number of lines to retrieve
            
        Returns:
            Dict with logs
        """
        logger.info(f"📋 Getting MCP logs for user: {user_id} (last {lines} lines)")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            log_file = f"/opt/mcp/instances/{user_id}/mcp.log"
            
            # Check if log file exists
            check_cmd = f"test -f {log_file} && echo 'exists' || echo 'not found'"
            stdin, stdout, stderr = client.exec_command(check_cmd)
            result = stdout.read().decode('utf-8').strip()
            
            if result != 'exists':
                return {
                    "success": False,
                    "error": f"Log file not found: {log_file}",
                    "user_id": user_id
                }
            
            # Get last N lines
            cmd = f"tail -n {lines} {log_file}"
            stdin, stdout, stderr = client.exec_command(cmd)
            
            logs = stdout.read().decode('utf-8')
            
            logger.info(f"✅ Retrieved {len(logs.splitlines())} log lines")
            
            return {
                "success": True,
                "user_id": user_id,
                "log_file": log_file,
                "lines": logs.splitlines(),
                "total_lines": len(logs.splitlines())
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get MCP logs: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()
    
    def get_system_logs(self, lines: int = 50) -> Dict:
        """
        Get system logs (syslog)
        
        Args:
            lines: Number of lines to retrieve
            
        Returns:
            Dict with logs
        """
        logger.info(f"📋 Getting system logs (last {lines} lines)")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            # Get recent system logs
            cmd = f"tail -n {lines} /var/log/syslog"
            stdin, stdout, stderr = client.exec_command(cmd)
            
            logs = stdout.read().decode('utf-8')
            
            logger.info(f"✅ Retrieved {len(logs.splitlines())} log lines")
            
            return {
                "success": True,
                "log_file": "/var/log/syslog",
                "lines": logs.splitlines(),
                "total_lines": len(logs.splitlines())
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get system logs: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()
    
    def tail_logs_realtime(self, user_id: str, log_type: str = "es", callback: Callable = None):
        """
        Tail logs in real-time
        
        Args:
            user_id: User ID
            log_type: "es" or "mcp"
            callback: Function to call with each new log line
        """
        logger.info(f"📺 Starting real-time log tail for {user_id} ({log_type})")
        
        client = self._get_ssh_client()
        if not client:
            if callback:
                callback({"error": "SSH connection failed"})
            return
        
        try:
            # Determine log file
            if log_type == "es":
                log_file = f"/opt/elasticsearch/instances/{user_id}/es.log"
            else:
                log_file = f"/opt/mcp/instances/{user_id}/mcp.log"
            
            # Start tailing
            cmd = f"tail -f {log_file}"
            transport = client.get_transport()
            channel = transport.open_session()
            channel.exec_command(cmd)
            
            # Store stream info
            stream_id = f"{user_id}_{log_type}"
            self.active_streams[stream_id] = {
                "client": client,
                "channel": channel,
                "user_id": user_id,
                "log_type": log_type,
                "active": True
            }
            
            logger.info(f"✅ Real-time tail started: {stream_id}")
            
            # Read output in loop
            while self.active_streams.get(stream_id, {}).get("active", False):
                if channel.recv_ready():
                    data = channel.recv(1024).decode('utf-8')
                    if callback:
                        callback({
                            "user_id": user_id,
                            "log_type": log_type,
                            "data": data
                        })
                time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"❌ Real-time tail failed: {e}")
            if callback:
                callback({"error": str(e)})
        finally:
            # Clean up
            stream_id = f"{user_id}_{log_type}"
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            client.close()
    
    def stop_tail(self, user_id: str, log_type: str = "es"):
        """Stop real-time tail"""
        stream_id = f"{user_id}_{log_type}"
        if stream_id in self.active_streams:
            self.active_streams[stream_id]["active"] = False
            logger.info(f"🛑 Stopped tail: {stream_id}")
    
    def list_log_files(self, user_id: str) -> Dict:
        """
        List all log files for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with log files
        """
        logger.info(f"📁 Listing log files for user: {user_id}")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            files = []
            
            # ES logs
            es_dir = f"/opt/elasticsearch/instances/{user_id}"
            cmd = f"ls -lh {es_dir}/*.log 2>/dev/null || echo 'no logs'"
            stdin, stdout, stderr = client.exec_command(cmd)
            es_logs = stdout.read().decode('utf-8')
            
            if 'no logs' not in es_logs:
                for line in es_logs.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 9:
                            files.append({
                                "path": parts[8],
                                "size": parts[4],
                                "modified": ' '.join(parts[5:8]),
                                "type": "elasticsearch"
                            })
            
            # MCP logs
            mcp_dir = f"/opt/mcp/instances/{user_id}"
            cmd = f"ls -lh {mcp_dir}/*.log 2>/dev/null || echo 'no logs'"
            stdin, stdout, stderr = client.exec_command(cmd)
            mcp_logs = stdout.read().decode('utf-8')
            
            if 'no logs' not in mcp_logs:
                for line in mcp_logs.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 9:
                            files.append({
                                "path": parts[8],
                                "size": parts[4],
                                "modified": ' '.join(parts[5:8]),
                                "type": "mcp"
                            })
            
            logger.info(f"✅ Found {len(files)} log files")
            
            return {
                "success": True,
                "user_id": user_id,
                "log_files": files,
                "total_count": len(files)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to list log files: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()
    
    def search_logs(self, user_id: str, search_term: str, log_type: str = "es") -> Dict:
        """
        Search logs for a specific term
        
        Args:
            user_id: User ID
            search_term: Term to search for
            log_type: "es" or "mcp"
            
        Returns:
            Dict with matching log lines
        """
        logger.info(f"🔍 Searching {log_type} logs for: {search_term}")
        
        client = self._get_ssh_client()
        if not client:
            return {"success": False, "error": "SSH connection failed"}
        
        try:
            # Determine log file
            if log_type == "es":
                log_file = f"/opt/elasticsearch/instances/{user_id}/es.log"
            else:
                log_file = f"/opt/mcp/instances/{user_id}/mcp.log"
            
            # Search with grep
            cmd = f"grep -n '{search_term}' {log_file} || echo 'no matches'"
            stdin, stdout, stderr = client.exec_command(cmd)
            
            results = stdout.read().decode('utf-8')
            
            if 'no matches' in results:
                return {
                    "success": True,
                    "user_id": user_id,
                    "search_term": search_term,
                    "matches": [],
                    "total_matches": 0
                }
            
            # Parse results
            matches = []
            for line in results.strip().split('\n'):
                if ':' in line:
                    line_num, content = line.split(':', 1)
                    matches.append({
                        "line_number": int(line_num),
                        "content": content.strip()
                    })
            
            logger.info(f"✅ Found {len(matches)} matches")
            
            return {
                "success": True,
                "user_id": user_id,
                "search_term": search_term,
                "log_type": log_type,
                "matches": matches,
                "total_matches": len(matches)
            }
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            client.close()
    
    def get_instance_health(self, user_id: str) -> Dict:
        """
        Get health status from logs
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with health info
        """
        logger.info(f"🏥 Checking instance health for: {user_id}")
        
        # Get recent ES logs
        es_logs = self.get_es_logs(user_id, lines=50)
        
        # Get recent MCP logs
        mcp_logs = self.get_mcp_logs(user_id, lines=50)
        
        health = {
            "user_id": user_id,
            "elasticsearch": {
                "has_logs": es_logs.get("success", False),
                "errors": [],
                "warnings": [],
                "status": "unknown"
            },
            "mcp": {
                "has_logs": mcp_logs.get("success", False),
                "errors": [],
                "warnings": [],
                "status": "unknown"
            }
        }
        
        # Check ES logs for errors/warnings
        if es_logs.get("success"):
            for line in es_logs.get("lines", []):
                if "ERROR" in line.upper():
                    health["elasticsearch"]["errors"].append(line)
                elif "WARN" in line.upper():
                    health["elasticsearch"]["warnings"].append(line)
                elif "started" in line.lower() or "green" in line.lower():
                    health["elasticsearch"]["status"] = "healthy"
        
        # Check MCP logs for errors/warnings
        if mcp_logs.get("success"):
            for line in mcp_logs.get("lines", []):
                if "ERROR" in line.upper() or "error" in line:
                    health["mcp"]["errors"].append(line)
                elif "WARN" in line.upper() or "warning" in line:
                    health["mcp"]["warnings"].append(line)
                elif "started" in line.lower() or "listening" in line.lower():
                    health["mcp"]["status"] = "healthy"
        
        logger.info(f"✅ Health check complete")
        logger.info(f"   ES Status: {health['elasticsearch']['status']}")
        logger.info(f"   MCP Status: {health['mcp']['status']}")
        
        return health


# Singleton instance
_log_viewer = None

def get_log_viewer(ssh_password: str = None, ssh_key_path: str = None) -> RemoteLogViewer:
    """Get or create log viewer"""
    global _log_viewer
    if _log_viewer is None:
        _log_viewer = RemoteLogViewer(
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path
        )
    return _log_viewer
