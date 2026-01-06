from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests


class ServiceNowClient:
    def __init__(self, instance_url: str, username: str, password: str):
        self.instance_url = instance_url.rstrip("/")
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.instance_url}/{path.lstrip('/')}"

    def validate(self) -> Dict[str, Any]:
        # lightweight auth check
        url = self._url("/api/now/table/sys_user")
        r = self.session.get(url, params={"sysparm_limit": "1"}, auth=self.auth, timeout=20)
        r.raise_for_status()
        return r.json()

    def list_tables(self, *, limit: int = 50, query: Optional[str] = None) -> List[Dict[str, Any]]:
        url = self._url("/api/now/table/sys_db_object")
        params = {
            "sysparm_fields": "name,label",
            "sysparm_limit": str(max(1, min(limit, 500))),
        }
        if query:
            # filter by name or label
            # ServiceNow sysparm_query uses ^ for AND
            params["sysparm_query"] = f"nameLIKE{query}^ORlabelLIKE{query}"
        r = self.session.get(url, params=params, auth=self.auth, timeout=30)
        r.raise_for_status()
        data = r.json() or {}
        return data.get("result", []) or []
