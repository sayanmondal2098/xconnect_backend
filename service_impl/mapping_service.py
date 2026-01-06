from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from base_requests import (
    CreateMappingRequest, MappingResponse, MappingListResponse,
    MappingValidationRequest, MappingValidationResponse,
    AutoMappingRequest, AutoMappingResponse,
)
from impl.db.session import SessionLocal
from impl.db.models import Integration, Mapping
from impl.integrations.github.client import GitHubClient
from impl.integrations.servicenow.client import ServiceNowClient
from impl.secret_store.factory import get_secret_store
from impl.utils.json_utils import dumps, loads


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MappingService:
    _DIRECTIONS = {"github_to_servicenow", "servicenow_to_github", "bidirectional"}
    _FUZZY_THRESHOLD = 0.78

    def _normalize_direction(self, direction: str) -> str:
        d = (direction or "").strip().lower()
        if d not in self._DIRECTIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="direction must be github_to_servicenow, servicenow_to_github, or bidirectional")
        return d

    def _get_github_client(self, db: Session, *, user_id: int, label: str = "default") -> tuple[GitHubClient, Integration]:
        row = (
            db.query(Integration)
            .filter(Integration.user_id == user_id, Integration.provider == "github", Integration.label == label)
            .first()
        )
        if not row or not row.secret_ref:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub integration not configured")

        store = get_secret_store(db)
        token = store.get(user_id=user_id, ref=row.secret_ref)
        client = GitHubClient(token)
        return client, row

    def _get_servicenow_client(self, db: Session, *, user_id: int, label: str = "default") -> tuple[ServiceNowClient, Integration]:
        row = (
            db.query(Integration)
            .filter(Integration.user_id == user_id, Integration.provider == "servicenow", Integration.label == label)
            .first()
        )
        if not row or not row.secret_ref:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ServiceNow integration not configured")

        cfg = loads(row.config_json or "{}")
        instance_url = cfg.get("instance_url")
        username = cfg.get("username")
        if not instance_url or not username:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ServiceNow integration config incomplete")

        store = get_secret_store(db)
        password = store.get(user_id=user_id, ref=row.secret_ref)
        client = ServiceNowClient(str(instance_url), str(username), str(password))
        return client, row

    @staticmethod
    def _normalize_name(name: str) -> str:
        return "".join(ch for ch in name.lower() if ch.isalnum())

    def _suggest_mapping(self, sn_fields: list[str], gh_fields: list[str]) -> tuple[dict[str, str], list[str]]:
        notes: list[str] = []
        mapping: dict[str, str] = {}
        gh_norm_map = {self._normalize_name(f): f for f in gh_fields}

        synonyms = {
            "shortdescription": ["description", "name"],
            "description": ["description", "body", "readme"],
            "state": ["state", "status", "visibility"],
            "priority": ["priority"],
            "assignmentgroup": ["owner_login", "owner", "organization"],
            "assignedto": ["owner_login", "owner"],
            "summary": ["description", "name"],
        }

        for sn in sn_fields:
            norm = self._normalize_name(sn)
            chosen = None
            if norm in gh_norm_map:
                chosen = gh_norm_map[norm]
                notes.append(f"Matched {sn} to GitHub field {chosen} by name")
            else:
                for candidate in synonyms.get(norm, []):
                    cnorm = self._normalize_name(candidate)
                    if cnorm in gh_norm_map:
                        chosen = gh_norm_map[cnorm]
                        notes.append(f"Mapped {sn} to GitHub field {chosen} via synonym")
                        break
            if not chosen:
                chosen, score = self._fuzzy_match(norm, gh_norm_map)
                if chosen:
                    notes.append(f"AI fuzzy matched {sn} to GitHub field {chosen} (score={score:.2f})")
            if chosen:
                mapping[sn] = chosen

        return mapping, notes

    def _fuzzy_match(self, norm_sn: str, gh_norm_map: dict[str, str]) -> tuple[str | None, float]:
        best = (None, 0.0)
        for gh_norm, gh_field in gh_norm_map.items():
            score = SequenceMatcher(a=norm_sn, b=gh_norm).ratio()
            if score > best[1]:
                best = (gh_field, score)
        if best[0] and best[1] >= self._FUZZY_THRESHOLD:
            return best[0], best[1]
        return None, 0.0

    def _basic_validate_mapping(self, mapping: dict[str, str], direction: str) -> None:
        errors: list[str] = []
        for sn_field, gh_field in mapping.items():
            if not str(sn_field).strip():
                errors.append("ServiceNow field names must be non-empty")
            if not str(gh_field).strip():
                errors.append(f"GitHub field for '{sn_field}' must be non-empty")

        if direction == "bidirectional":
            seen: set[str] = set()
            duplicates: set[str] = set()
            for gh_field in mapping.values():
                if gh_field in seen:
                    duplicates.add(gh_field)
                seen.add(gh_field)
            if duplicates:
                errors.append(
                    "Bidirectional mappings must be one-to-one. "
                    f"Duplicate GitHub targets: {', '.join(sorted(duplicates))}"
                )

        if errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    def create(self, *, user_id: int, req: CreateMappingRequest) -> MappingResponse:
        with SessionLocal() as db:
            # basic validation of repo format
            if "/" not in req.github_repo_full_name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="github_repo_full_name must be like owner/repo")

            direction = self._normalize_direction(req.direction)
            field_mapping = req.field_mapping or {}
            self._basic_validate_mapping(field_mapping, direction)
            mapping_json = dumps(field_mapping)

            row = Mapping(
                user_id=user_id,
                github_repo_full_name=req.github_repo_full_name.strip(),
                servicenow_table=req.servicenow_table.strip(),
                label=req.label.strip() or "default",
                direction=direction,
                field_mapping_json=mapping_json,
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
                direction=row.direction,
                field_mapping=loads(row.field_mapping_json or "{}"),
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
                    direction=r.direction,
                    field_mapping=loads(r.field_mapping_json or "{}"),
                    created_at=r.created_at.isoformat(),
                )
                for r in rows
            ]
            return MappingListResponse(ok=True, items=items)

    def validate(self, *, user_id: int, req: MappingValidationRequest) -> MappingValidationResponse:
        if "/" not in req.github_repo_full_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="github_repo_full_name must be like owner/repo")

        direction = self._normalize_direction(req.direction)
        mapping = req.field_mapping or {}
        self._basic_validate_mapping(mapping, direction)

        with SessionLocal() as db:
            gh, gh_row = self._get_github_client(db, user_id=user_id, label=req.label)
            sn, sn_row = self._get_servicenow_client(db, user_id=user_id, label=req.label)

            try:
                repo_raw = gh.get_repo(req.github_repo_full_name.strip())
                sn_fields_raw = sn.list_fields(table=req.servicenow_table.strip())
                gh_row.last_tested_at = sn_row.last_tested_at = datetime.now(timezone.utc)
                gh_row.last_test_ok = sn_row.last_test_ok = True
                gh_row.last_test_message = sn_row.last_test_message = "OK"
                db.commit()
            except Exception as e:
                msg = str(e)[:500]
                gh_row.last_tested_at = sn_row.last_tested_at = datetime.now(timezone.utc)
                gh_row.last_test_ok = sn_row.last_test_ok = False
                gh_row.last_test_message = sn_row.last_test_message = msg
                db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation failed: {e}")

        gh_fields = [k for k in repo_raw.keys() if isinstance(k, str)]
        sn_fields = [str(f.get("element")) for f in sn_fields_raw if f.get("element")]
        sn_required = [str(f.get("element")) for f in sn_fields_raw if f.get("mandatory")]

        missing_sn = [k for k in mapping.keys() if k not in sn_fields]
        missing_gh = [v for v in mapping.values() if v not in gh_fields]

        warnings: list[str] = []
        missing_required = [f for f in sn_required if f not in mapping]
        if missing_required and direction in ("github_to_servicenow", "bidirectional"):
            warnings.append(f"Missing required ServiceNow fields: {', '.join(missing_required)}")

        suggested, notes = self._suggest_mapping(sn_fields, gh_fields)

        return MappingValidationResponse(
            ok=not missing_sn and not missing_gh,
            suggested_mapping=suggested,
            missing_servicenow_fields=missing_sn,
            missing_github_fields=missing_gh,
            warnings=warnings + notes,
        )

    def auto_map(self, *, user_id: int, req: AutoMappingRequest) -> AutoMappingResponse:
        if "/" not in req.github_repo_full_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="github_repo_full_name must be like owner/repo")
        self._normalize_direction(req.direction)

        with SessionLocal() as db:
            gh, gh_row = self._get_github_client(db, user_id=user_id, label=req.label)
            sn, sn_row = self._get_servicenow_client(db, user_id=user_id, label=req.label)

            try:
                repo_raw = gh.get_repo(req.github_repo_full_name.strip())
                sn_fields_raw = sn.list_fields(table=req.servicenow_table.strip())
                gh_row.last_tested_at = sn_row.last_tested_at = datetime.now(timezone.utc)
                gh_row.last_test_ok = sn_row.last_test_ok = True
                gh_row.last_test_message = sn_row.last_test_message = "OK"
                db.commit()
            except Exception as e:
                msg = str(e)[:500]
                gh_row.last_tested_at = sn_row.last_tested_at = datetime.now(timezone.utc)
                gh_row.last_test_ok = sn_row.last_test_ok = False
                gh_row.last_test_message = sn_row.last_test_message = msg
                db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Auto mapping failed: {e}")

        gh_fields = [k for k in repo_raw.keys() if isinstance(k, str)]
        sn_fields = [str(f.get("element")) for f in sn_fields_raw if f.get("element")]
        mapping, notes = self._suggest_mapping(sn_fields, gh_fields)

        return AutoMappingResponse(ok=True, mapping=mapping, notes=notes)
