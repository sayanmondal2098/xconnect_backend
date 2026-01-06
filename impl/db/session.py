from __future__ import annotations

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from impl.config import settings
from impl.db.models import Base


_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def _sqlite_add_column_if_missing(table: str, col: str, ddl: str) -> None:
    if _engine.dialect.name != "sqlite":
        return

    insp = inspect(_engine)
    existing = {c["name"] for c in insp.get_columns(table)}
    if col in existing:
        return

    with _engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def init_db() -> None:
    """Create tables and apply lightweight SQLite migrations.

    SQLAlchemy's create_all() won't add columns to existing SQLite tables.
    Since this is an MVP repo (not a full Alembic migration story), we do
    a tiny best-effort ALTER TABLE for new columns we introduced.
    """

    Base.metadata.create_all(bind=_engine)

    # Add integration health columns if upgrading an existing DB
    _sqlite_add_column_if_missing(
        "integrations",
        "last_tested_at",
        "last_tested_at DATETIME",
    )
    _sqlite_add_column_if_missing(
        "integrations",
        "last_test_ok",
        "last_test_ok BOOLEAN",
    )
    _sqlite_add_column_if_missing(
        "integrations",
        "last_test_message",
        "last_test_message TEXT",
    )
    _sqlite_add_column_if_missing(
        "mappings",
        "direction",
        "direction VARCHAR(30) NOT NULL DEFAULT 'bidirectional'",
    )
    _sqlite_add_column_if_missing(
        "mappings",
        "field_mapping_json",
        "field_mapping_json TEXT NOT NULL DEFAULT '{}'",
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
