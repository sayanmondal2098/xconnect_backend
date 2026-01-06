from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from base_requests import CreateMappingRequest, MappingResponse, MappingListResponse
from impl.db.session import SessionLocal
from impl.db.models import Mapping


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MappingService:
    def create(self, *, user_id: int, req: CreateMappingRequest) -> MappingResponse:
        with SessionLocal() as db:
            # basic validation of repo format
            if "/" not in req.github_repo_full_name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="github_repo_full_name must be like owner/repo")

            row = Mapping(
                user_id=user_id,
                github_repo_full_name=req.github_repo_full_name.strip(),
                servicenow_table=req.servicenow_table.strip(),
                label=req.label.strip() or "default",
            )
            db.add(row)
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mapping already exists")

            db.refresh(row)
            return MappingResponse(
                id=row.id,
                github_repo_full_name=row.github_repo_full_name,
                servicenow_table=row.servicenow_table,
                label=row.label,
                created_at=row.created_at.isoformat(),
            )

    def list(self, *, user_id: int) -> MappingListResponse:
        with SessionLocal() as db:
            rows = db.query(Mapping).filter(Mapping.user_id == user_id).order_by(Mapping.id.desc()).all()
            items = [
                MappingResponse(
                    id=r.id,
                    github_repo_full_name=r.github_repo_full_name,
                    servicenow_table=r.servicenow_table,
                    label=r.label,
                    created_at=r.created_at.isoformat(),
                )
                for r in rows
            ]
            return MappingListResponse(ok=True, items=items)
