import requests
import time
from typing import Optional, Dict, Any, List

class DBUserRegistry:
    """Wrapper for the external user DB API.
    Expected user document shape (extensible):
      {
        "UserId": "<id>",
        "ofELK": "1",                 # always '1'
        "es_host": "http://host",      # optional
        "es_port": 9200,                # optional
        "mcp_url": "http://host:10200",# optional
        "indices": ["upload-..."],      # optional
        "last_updated": "ISO8601"       # optional metadata
      }
    The API provided: POST/GET to /users . We'll use simple conventions:
      - GET {base}/users?UserId=<id>  (if supported) else fallback to POST for create.
      - POST {base}/users with JSON body (create or upsert).
    If the API actually differs, adjust endpoints accordingly.
    """

    def __init__(self, base_url: str, timeout: float = 4.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _safe(self, func, default=None):
        try:
            return func()
        except Exception:
            return default

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        def op():
            url = f"{self.base_url}/users/{user_id}"
            print(f"[DBUserRegistry] GET {url}")
            r = requests.get(url, timeout=self.timeout)
            print(f"[DBUserRegistry] GET status={r.status_code} body={r.text[:200]}")
            if r.status_code == 200:
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        return data
                except Exception as e:
                    print(f"[DBUserRegistry] GET parse error: {e}")
            return None
        return self._safe(op)

    def create_or_update_user(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = dict(payload)
        # ofELK must equal the user id per new requirement
        if payload.get('UserId'):
            payload['ofELK'] = str(payload['UserId'])
        else:
            # fallback: if only ofELK provided treat it as UserId
            if 'ofELK' in payload and 'UserId' not in payload:
                payload['UserId'] = str(payload['ofELK'])
        def op():
            url = f"{self.base_url}/users"
            print(f"[DBUserRegistry] POST {url} payload={payload}")
            r = requests.post(url, json=payload, timeout=self.timeout)
            print(f"[DBUserRegistry] POST status={r.status_code} body={r.text[:250]}")
            if r.status_code in (200, 201):
                try:
                    return r.json()
                except Exception:
                    return payload
            return None
        return self._safe(op, payload)

    def ensure_user(self, user_id: str) -> Dict[str, Any]:
        print(f"[DBUserRegistry] ensure_user called user_id={user_id}")
        user = self.get_user(user_id)
        if user:
            print(f"[DBUserRegistry] existing user found keys={list(user.keys())}")
            # Normalize fields
            user['ofELK'] = str(user.get('UserId', user_id))
            user.setdefault('indices', [])
            return user
        # Create minimal user
        new_user = {
            'UserId': str(user_id),
            'ofELK': str(user_id),
            'indices': []
        }
        print(f"[DBUserRegistry] creating new user payload={new_user}")
        created = self.create_or_update_user(new_user) or new_user
        print(f"[DBUserRegistry] ensure_user created response={created}")
        return created

    def update_instances(self, user: Dict[str, Any], es_host: str, es_port: int, mcp_url: str = None, indices: List[str] = None):
        print(f"[DBUserRegistry] update_instances start host={es_host} port={es_port} mcp_url={mcp_url} indices_count={(len(indices) if indices else 0)}")
        payload = dict(user)
        payload['es_host'] = es_host
        payload['es_port'] = es_port
        # Maintain invariant ofELK == UserId
        if payload.get('UserId'):
            payload['ofELK'] = str(payload['UserId'])
        if mcp_url:
            payload['mcp_url'] = mcp_url
        if indices is not None:
            payload['indices'] = indices
        resp = self.create_or_update_user(payload)
        print(f"[DBUserRegistry] update_instances response={resp}")

    def append_index(self, user: Dict[str, Any], new_index: str):
        print(f"[DBUserRegistry] append_index new_index={new_index}")
        indices = list(user.get('indices') or [])
        if new_index not in indices:
            indices.append(new_index)
            self.update_instances(user, user.get('es_host'), user.get('es_port'), user.get('mcp_url'), indices)
        else:
            print(f"[DBUserRegistry] append_index skipped duplicate={new_index}")

