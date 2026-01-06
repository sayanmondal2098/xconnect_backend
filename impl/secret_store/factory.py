from __future__ import annotations

from sqlalchemy.orm import Session

from impl.config import settings
from impl.secret_store.interfaces import SecretStore
from impl.secret_store.sqlite_store import SQLiteSecretStore
from impl.secret_store.aws_store import AWSSecretsManagerStore


def get_secret_store(db: Session) -> SecretStore:
    if settings.secret_store == "aws":
        return AWSSecretsManagerStore()
    return SQLiteSecretStore(db)
