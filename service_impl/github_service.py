from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from base_requests import GithubConnectRequest, GithubConnectResponse, GithubRepo, GithubRepoListResponse
from impl.db.session import SessionLocal
from impl.db.models import Integration
from impl.secret_store.factory import get_secret_store
from impl.integrations.github.client import GitHubClient
from impl.utils.json_utils import dumps


def _utc_now():
    return datetime.now(timezone.utc)

class GithubService:
    PROVIDER = "github"

    def connect(self, *, user_id: int, req: GithubConnectRequest) -> GithubConnectResponse:
        with SessionLocal() as db:
            # validate token first
            try:
                gh = GitHubClient(req.token)
                me = gh.get_user()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GitHub auth failed: {e}")

            store = get_secret_store(db)
            secret_ref = store.put(user_id=user_id, name=f"github_token:{req.label}", value=req.token)

            cfg = {"type": "pat", "github_user_id": int(me.get("id", 0)), "github_login": str(me.get("login", ""))}
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user_id, Integration.provider == self.PROVIDER, Integration.label == req.label)
                .first()
            )
            if row:
                row.config_json = dumps(cfg)
                row.secret_ref = secret_ref
            else:
                row = Integration(user_id=user_id, provider=self.PROVIDER, label=req.label, config_json=dumps(cfg), secret_ref=secret_ref)
                db.add(row)

            row.last_tested_at = _utc_now()
            row.last_test_ok = True
            row.last_test_message = "OK"

            db.commit()

            return GithubConnectResponse(
                ok=True,
                label=req.label,
                github_login=str(me.get("login", "")),
                github_user_id=int(me.get("id", 0)),
            )

    def list_repos(self, *, user_id: int, label: str = "default") -> GithubRepoListResponse:
        with SessionLocal() as db:
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user_id, Integration.provider == self.PROVIDER, Integration.label == label)
                .first()
            )
            if not row or not row.secret_ref:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub integration not configured")

            store = get_secret_store(db)
            token = store.get(user_id=user_id, ref=row.secret_ref)

            try:
                gh = GitHubClient(token)
                repos_raw = gh.list_repos()

                row.last_tested_at = _utc_now()
                row.last_test_ok = True
                row.last_test_message = "OK"
                db.commit()
            except Exception as e:
                row.last_tested_at = _utc_now()
                row.last_test_ok = False
                row.last_test_message = str(e)[:500]
                db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GitHub API failed: {e}")

            repos = [
                GithubRepo(
                    id=int(r.get("id", 0)),
                    full_name=str(r.get("full_name", "")),
                    private=bool(r.get("private", False)),
                    html_url=str(r.get("html_url", "")),
                )
                for r in repos_raw
                if r.get("full_name")
            ]
            return GithubRepoListResponse(ok=True, repos=repos)
