from __future__ import annotations

from typing import Any, Dict, List
import requests


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        })

    def get_user(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/user", timeout=20)
        r.raise_for_status()
        return r.json()

    def list_repos(self) -> List[Dict[str, Any]]:
        # basic pagination (up to 200 repos)
        repos: List[Dict[str, Any]] = []
        url = f"{self.base_url}/user/repos"
        params = {"per_page": 100, "sort": "updated"}
        for _ in range(2):
            r = self.session.get(url, params=params, timeout=30)
            r.raise_for_status()
            repos.extend(r.json())
            # GitHub pagination in Link header
            link = r.headers.get("Link", "")
            next_url = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>").strip()
            if not next_url:
                break
            url = next_url
            params = None
        return repos

    def get_repo(self, full_name: str) -> Dict[str, Any]:
        full_name = full_name.strip().rstrip("/")
        url = f"{self.base_url}/repos/{full_name}"
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
