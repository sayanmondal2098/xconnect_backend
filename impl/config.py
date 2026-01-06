from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


ROOT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "XConnect Backend"
    env: str = "dev"

    database_url: str = "sqlite:///./xconnect.db"

    jwt_secret_key: str = "change_me_in_prod"
    jwt_access_token_expire_minutes: int = 60

    secret_store: str = "sqlite"  # sqlite | aws
    encryption_key: str = ""      # required for sqlite secret store

    aws_region: str = "ap-south-1"
    aws_secret_prefix: str = "xconnect"

    cors_allow_origins: str = "*"

    @field_validator("secret_store")
    @classmethod
    def _validate_secret_store(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in ("sqlite", "aws"):
            raise ValueError("SECRET_STORE must be 'sqlite' or 'aws'")
        return v

    @property
    def cors_allow_origins_list(self) -> List[str]:
        s = (self.cors_allow_origins or "").strip()
        if not s:
            return []
        if s == "*":
            return ["*"]
        return [x.strip() for x in s.split(",") if x.strip()]


settings = Settings()
