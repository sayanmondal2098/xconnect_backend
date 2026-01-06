from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from base_requests import (
    ServiceNowConnectRequest, ServiceNowConnectResponse,
    ServiceNowTable, ServiceNowTableListResponse,
    ServiceNowField, ServiceNowFieldListResponse, ServiceNowRecordUpsertRequest, ServiceNowRecordResponse,
)
from impl.db.session import SessionLocal
from impl.db.models import Integration
from impl.secret_store.factory import get_secret_store
from impl.integrations.servicenow.client import ServiceNowClient
from impl.utils.json_utils import dumps, loads


def _utc_now():
    return datetime.now(timezone.utc)


class ServiceNowService:
    PROVIDER = "servicenow"

    def connect(self, *, user_id: int, req: ServiceNowConnectRequest) -> ServiceNowConnectResponse:
        with SessionLocal() as db:
            # validate credentials first
            try:
                sn = ServiceNowClient(str(req.instance_url), req.username, req.password)
                sn.validate()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ServiceNow auth failed: {e}")

            store = get_secret_store(db)
            secret_ref = store.put(user_id=user_id, name=f"servicenow_password:{req.label}", value=req.password)

            cfg = {"instance_url": str(req.instance_url), "username": req.username}
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

            return ServiceNowConnectResponse(ok=True, label=req.label, instance_url=req.instance_url, user=req.username)

    def _get_client(self, db: Session, *, user_id: int, label: str = "default") -> tuple[ServiceNowClient, Integration]:
        row = (
            db.query(Integration)
            .filter(Integration.user_id == user_id, Integration.provider == self.PROVIDER, Integration.label == label)
            .first()
        )
        if not row or not row.secret_ref:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ServiceNow integration not configured")

        cfg = loads(row.config_json)
        instance_url = cfg.get("instance_url")
        username = cfg.get("username")
        if not instance_url or not username:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ServiceNow integration config incomplete")

        store = get_secret_store(db)
        password = store.get(user_id=user_id, ref=row.secret_ref)
        client = ServiceNowClient(str(instance_url), str(username), str(password))
        return client, row

    def list_tables(self, *, user_id: int, limit: int = 50, query: str | None = None, label: str = "default") -> ServiceNowTableListResponse:
        with SessionLocal() as db:
            sn, irow = self._get_client(db, user_id=user_id, label=label)
            try:
                rows = sn.list_tables(limit=limit, query=query)

                irow.last_tested_at = _utc_now()
                irow.last_test_ok = True
                irow.last_test_message = "OK"
                db.commit()
            except Exception as e:
                irow.last_tested_at = _utc_now()
                irow.last_test_ok = False
                irow.last_test_message = str(e)[:500]
                db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ServiceNow API failed: {e}")

            tables = [ServiceNowTable(name=str(r.get("name","")), label=r.get("label")) for r in rows if r.get("name")]
            return ServiceNowTableListResponse(ok=True, tables=tables, returned=len(tables))

    def list_fields(self, *, user_id: int, table: str, label: str = "default") -> ServiceNowFieldListResponse:
        table_name = table.strip()
        if not table_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="table is required")

        with SessionLocal() as db:
            sn, irow = self._get_client(db, user_id=user_id, label=label)
            try:
                rows = sn.list_fields(table=table_name)

                irow.last_tested_at = _utc_now()
                irow.last_test_ok = True
                irow.last_test_message = "OK"
                db.commit()
            except Exception as e:
                irow.last_tested_at = _utc_now()
                irow.last_test_ok = False
                irow.last_test_message = str(e)[:500]
                db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ServiceNow API failed: {e}")

            fields: list[ServiceNowField] = []
            for r in rows:
                name = str(r.get("element", "")).strip()
                if not name:
                    continue
                fields.append(
                    ServiceNowField(
                        name=name,
                        label=r.get("column_label") or r.get("label"),
                        mandatory=bool(r.get("mandatory")),
                        type=r.get("internal_type"),
                        reference=r.get("reference"),
                        max_length=int(r.get("max_length")) if str(r.get("max_length") or "").isdigit() else None,
                    )
                )

            return ServiceNowFieldListResponse(ok=True, table=table_name, fields=fields, returned=len(fields))

    def upsert_record(self, *, user_id: int, req: ServiceNowRecordUpsertRequest) -> ServiceNowRecordResponse:
        table_name = req.table.strip()
        if not table_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="table is required")
        if not req.data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="data is required")

        with SessionLocal() as db:
            sn, irow = self._get_client(db, user_id=user_id, label=req.label)
            try:
                if req.sys_id:
                    raw = sn.update_record(table=table_name, sys_id=req.sys_id, payload=req.data)
                    action = "updated"
                else:
                    raw = sn.create_record(table=table_name, payload=req.data)
                    action = "created"

                irow.last_tested_at = _utc_now()
                irow.last_test_ok = True
                irow.last_test_message = "OK"
                db.commit()
            except Exception as e:
                irow.last_tested_at = _utc_now()
                irow.last_test_ok = False
                irow.last_test_message = str(e)[:500]
                db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ServiceNow API failed: {e}")

            result = raw.get("result") if isinstance(raw, dict) else None
            sys_id = ""
            if isinstance(result, dict):
                sys_id = str(result.get("sys_id") or req.sys_id or "")

            return ServiceNowRecordResponse(
                ok=True,
                table=table_name,
                sys_id=sys_id,
                action=action,
                record=result or raw or {},
            )
