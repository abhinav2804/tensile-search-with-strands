"""
Modular Database Module - FULL API MODE
========================================
Integrated with Real API: http://82.112.235.26:4000

API ENDPOINTS:
✅ POST /users - Create user (WORKING)
✅ GET /users/{UserId} - Get user by ID (WORKING)
⚠️ PATCH/PUT /users/{UserId} - Update user (NOT IMPLEMENTED - uses local cache)

All operations use real API where available!
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List
import logging
import requests

logger = logging.getLogger(__name__)

class DatabaseModule:
    """
    Abstraction layer for user database with full API integration
    """
    
    def __init__(self, storage_type="api", api_base_url=None):
        """
        Initialize database module
        
        Args:
            storage_type: "local" or "api" (default: "api")
                - local: All operations use local JSON
                - api: All operations use real API with local cache for fallback
            api_base_url: Base URL for real API
        """
        self.storage_type = storage_type
        self.api_base_url = api_base_url or "http://82.112.235.26:4000"
        self.local_db_file = "data/user_database.json"
        
        # Always ensure local DB exists (for caching and fallback)
        self._ensure_local_db()
        
        logger.info(f"🚀 DatabaseModule initialized: {storage_type} mode")
        if storage_type == "api":
            logger.info(f"📡 API Base URL: {self.api_base_url}")
            logger.info(f"✅ Using REAL API for CREATE and GET operations")
    
    def _ensure_local_db(self):
        """Ensure local database file exists"""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.local_db_file):
            with open(self.local_db_file, 'w') as f:
                json.dump({"users": {}}, f, indent=2)
    
    def _read_local_db(self) -> dict:
        """Read local database"""
        try:
            with open(self.local_db_file, 'r') as f:
                return json.load(f)
        except:
            return {"users": {}}
    
    def _write_local_db(self, data: dict):
        """Write to local database"""
        with open(self.local_db_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID - Uses real API!"""
        logger.info(f"📊 DB: Getting user {user_id}")
        
        if self.storage_type == "local":
            db = self._read_local_db()
            user = db["users"].get(user_id)
            if user:
                logger.info(f"✅ User found locally: {user.get('email', 'N/A')}")
            else:
                logger.info(f"⚠️ User not found locally")
            return user
        else:
            # API mode - Use real API!
            try:
                url = f"{self.api_base_url}/users/{user_id}"
                logger.info(f"🌐 API GET: {url}")
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    user_data = response.json()
                    logger.info(f"✅ User found via API: {user_data.get('email', 'N/A')}")
                    
                    # Cache the user locally for UPDATE fallback
                    db = self._read_local_db()
                    db["users"][user_id] = user_data
                    self._write_local_db(db)
                    
                    return user_data
                elif response.status_code == 404:
                    logger.info(f"⚠️ User not found in API")
                    # Check local cache as fallback
                    db = self._read_local_db()
                    cached_user = db["users"].get(user_id)
                    if cached_user:
                        logger.info(f"📦 Found in local cache")
                    return cached_user
                else:
                    logger.error(f"❌ API Error: {response.status_code}")
                    # Fallback to local cache
                    db = self._read_local_db()
                    return db["users"].get(user_id)
            except Exception as e:
                logger.error(f"❌ API Request failed: {str(e)}")
                # Fallback to local cache
                db = self._read_local_db()
                return db["users"].get(user_id)
    
    def create_user(self, user_data: Dict) -> Dict:
        """Create new user - Uses real API!"""
        logger.info(f"📝 DB: Creating user {user_data.get('email', 'N/A')}")
        
        if self.storage_type == "local":
            # Local-only mode
            db = self._read_local_db()
            user_id = user_data['user_id']
            user_data['created_at'] = datetime.now().isoformat()
            user_data['updated_at'] = datetime.now().isoformat()
            db["users"][user_id] = user_data
            self._write_local_db(db)
            logger.info(f"✅ User created locally")
            return user_data
        else:
            # API mode - Use real API!
            try:
                api_payload = {
                    "UserId": user_data.get('user_id'),
                    "ofELK": user_data.get('ofELK', '0'),
                    "name": user_data.get('name', ''),
                    "email": user_data.get('email', '')
                }
                
                # Include any additional fields
                for key, value in user_data.items():
                    if key not in ['user_id', 'ofELK', 'name', 'email']:
                        api_payload[key] = value
                
                url = f"{self.api_base_url}/users"
                logger.info(f"🌐 API POST: {url}")
                logger.info(f"📦 Payload: {json.dumps(api_payload, indent=2)}")
                
                response = requests.post(
                    url,
                    json=api_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    created_user = response.json()
                    logger.info(f"✅ User created via API: {api_payload['email']}")
                    
                    # Cache locally for UPDATE fallback
                    db = self._read_local_db()
                    db["users"][user_data['user_id']] = {
                        **user_data,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    self._write_local_db(db)
                    logger.info(f"💾 Cached locally")
                    
                    return created_user
                else:
                    logger.error(f"❌ API Error: {response.status_code} - {response.text}")
                    return user_data
            except Exception as e:
                logger.error(f"❌ API Request failed: {str(e)}")
                return user_data
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """
        Update user - Uses local cache (API UPDATE not implemented yet)
        
        Note: When API UPDATE endpoint is ready, this will use API first,
        then fall back to local cache only on error.
        """
        logger.info(f"🔄 DB: Updating user {user_id}")
        logger.info(f"   Updates: {json.dumps(updates, indent=2)}")
        
        if self.storage_type == "local":
            db = self._read_local_db()
            if user_id in db["users"]:
                db["users"][user_id].update(updates)
                db["users"][user_id]['updated_at'] = datetime.now().isoformat()
                self._write_local_db(db)
                logger.info(f"✅ User updated locally")
                return True
            else:
                logger.warning(f"⚠️ User not found locally")
                return False
        else:
            # API mode - use local cache for now (API UPDATE returns 500)
            logger.info(f"⚠️ Using local cache (API UPDATE not implemented yet)")
            db = self._read_local_db()
            if user_id in db["users"]:
                db["users"][user_id].update(updates)
                db["users"][user_id]['updated_at'] = datetime.now().isoformat()
                self._write_local_db(db)
                logger.info(f"✅ User updated in local cache")
                return True
            else:
                logger.warning(f"⚠️ User not found in local cache")
                return False
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email - Uses local cache (API doesn't support email query)
        
        Note: If API adds email query support, update this to use API first
        """
        logger.info(f"🔍 DB: Looking up user by email: {email}")
        
        # Use local cache for email lookup (API doesn't support this query yet)
        db = self._read_local_db()
        for user in db["users"].values():
            if user.get('email') == email:
                logger.info(f"✅ User found by email in cache")
                return user
        
        logger.info(f"⚠️ User not found by email")
        return None
    
    def update_es_node(self, user_id: str, es_config: Dict) -> bool:
        """Update Elasticsearch node configuration"""
        logger.info(f"🔧 DB: Updating ES node for user {user_id}")
        updates = {
            "elasticsearch": es_config,
            "has_elasticsearch": True
        }
        return self.update_user(user_id, updates)
    
    def update_mcp_node(self, user_id: str, mcp_config: Dict) -> bool:
        """Update MCP node configuration"""
        logger.info(f"🔌 DB: Updating MCP node for user {user_id}")
        updates = {
            "mcp": mcp_config,
            "has_mcp": True
        }
        return self.update_user(user_id, updates)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users - Uses local cache"""
        db = self._read_local_db()
        return list(db["users"].values())


# ============================================
# Singleton instance - FULL API MODE! 🚀
# ============================================
db = DatabaseModule(storage_type="api")


if __name__ == "__main__":
    # Test example
    user_data = {
        "user_id": "U123456",
        "email": "test@example.com",
        "name": "Test User",
        "ofELK": "1"
    }
    db.create_user(user_data)
    
    # Get user via API
    user = db.get_user("U123456")
    print(json.dumps(user, indent=2))
