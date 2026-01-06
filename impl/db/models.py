from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    integrations = relationship("Integration", back_populates="user", cascade="all,delete-orphan")
    mappings = relationship("Mapping", back_populates="user", cascade="all,delete-orphan")


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "label", name="uq_user_provider_label"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # github | servicenow
    label = Column(String(100), nullable=False, default="default")

    # provider-specific config (non-secret)
    config_json = Column(Text, nullable=False, default="{}")

    # reference to secret store (sqlite secret id or aws secret name/arn)
    secret_ref = Column(String(512), nullable=True)

    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_ok = Column(Boolean, nullable=True)
    last_test_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="integrations")


class Secret(Base):
    __tablename__ = "secrets"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_secret_name"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)

    # encrypted payload (sqlite secret store)
    ciphertext = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    theme = Column(String(30), nullable=False, default="dark")
    notifications = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Mapping(Base):
    __tablename__ = "mappings"
    __table_args__ = (
        UniqueConstraint("user_id", "github_repo_full_name", "servicenow_table", "label", name="uq_mapping"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    github_repo_full_name = Column(String(300), nullable=False)
    servicenow_table = Column(String(200), nullable=False)
    label = Column(String(100), nullable=False, default="default")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="mappings")
