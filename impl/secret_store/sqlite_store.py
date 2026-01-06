from __future__ import annotations

from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from impl.config import settings
from impl.utils.crypto_utils import get_or_create_fernet_key
from impl.db.models import Secret
from impl.secret_store.interfaces import SecretStore


def _utc_now():
    return datetime.now(timezone.utc)


class SQLiteSecretStore(SecretStore):
    def __init__(self, db: Session):
        # In prod, you should set ENCRYPTION_KEY.
        # In dev, we auto-generate a local Fernet key file so you can actually run the app.
        key = settings.encryption_key
        if not key and settings.env.lower() == "dev":
            key = get_or_create_fernet_key()
        if not key:
            raise RuntimeError("ENCRYPTION_KEY is required when SECRET_STORE=sqlite")

        self.db = db
        self.fernet = Fernet(key.encode("utf-8"))

    def put(self, *, user_id: int, name: str, value: str) -> str:
        ciphertext = self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        row = self.db.query(Secret).filter(Secret.user_id == user_id, Secret.name == name).first()
        if row:
            row.ciphertext = ciphertext
            row.updated_at = _utc_now()
        else:
            row = Secret(user_id=user_id, name=name, ciphertext=ciphertext, created_at=_utc_now(), updated_at=_utc_now())
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return f"sqlite:{row.id}"

    def get(self, *, user_id: int, ref: str) -> str:
        if not ref.startswith("sqlite:"):
            raise ValueError("Invalid sqlite secret ref")
        sid = int(ref.split(":", 1)[1])
        row = self.db.query(Secret).filter(Secret.id == sid, Secret.user_id == user_id).first()
        if not row:
            raise ValueError("Secret not found")
        return self.fernet.decrypt(row.ciphertext.encode("utf-8")).decode("utf-8")