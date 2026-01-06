from __future__ import annotations

from fastapi import HTTPException, status

from base_requests import IntegrationListResponse, IntegrationSummary
from impl.db.session import SessionLocal
from impl.db.models import Integration, Secret
from impl.utils.json_utils import loads


class IntegrationService:
    def list(self, *, user_id: int) -> IntegrationListResponse:
        with SessionLocal() as db:
            rows = (
                db.query(Integration)
                .filter(Integration.user_id == user_id)
                .order_by(Integration.provider.asc(), Integration.label.asc())
                .all()
            )

            items = []
            for r in rows:
                cfg = {}
                try:
                    cfg = loads(r.config_json)
                except Exception:
                    cfg = {}

                items.append(
                    IntegrationSummary(
                        id=r.id,
                        provider=r.provider,
                        label=r.label,
                        config=cfg,
                        created_at=r.created_at.isoformat() if r.created_at else "",
                        updated_at=r.updated_at.isoformat() if r.updated_at else "",
                        last_tested_at=r.last_tested_at.isoformat() if getattr(r, "last_tested_at", None) else None,
                        last_test_ok=bool(r.last_test_ok) if getattr(r, "last_test_ok", None) is not None else None,
                        last_test_message=getattr(r, "last_test_message", None),
                    )
                )

            return IntegrationListResponse(ok=True, items=items)

    def delete(self, *, user_id: int, provider: str, label: str) -> None:
        provider = (provider or "").strip().lower()
        label = (label or "default").strip()

        with SessionLocal() as db:
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user_id, Integration.provider == provider, Integration.label == label)
                .first()
            )
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

            # Best-effort secret cleanup for local sqlite store
            if row.secret_ref and str(row.secret_ref).startswith("sqlite:"):
                try:
                    sid = int(str(row.secret_ref).split(":", 1)[1])
                    srow = db.query(Secret).filter(Secret.id == sid, Secret.user_id == user_id).first()
                    if srow:
                        db.delete(srow)
                except Exception:
                    # don't fail deletion because cleanup is messy
                    pass

            db.delete(row)
            db.commit()
