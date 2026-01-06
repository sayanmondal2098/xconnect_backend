from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, HttpUrl


# ---------- Generic ----------
class HealthResponse(BaseModel):
    ok: bool


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class MeResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: str


class UpdateMeRequest(BaseModel):
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


# ---------- GitHub ----------
class GithubConnectRequest(BaseModel):
    # simplest: PAT token
    token: str = Field(min_length=10, max_length=4096)
    label: str = Field(default="default", max_length=100)


class GithubConnectResponse(BaseModel):
    ok: bool
    label: str
    github_login: str
    github_user_id: int


class GithubRepo(BaseModel):
    id: int
    full_name: str
    private: bool
    html_url: HttpUrl


class GithubRepoListResponse(BaseModel):
    ok: bool
    repos: List[GithubRepo]


# ---------- ServiceNow ----------
class ServiceNowConnectRequest(BaseModel):
    instance_url: HttpUrl
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=4096)
    label: str = Field(default="default", max_length=100)


class ServiceNowConnectResponse(BaseModel):
    ok: bool
    label: str
    instance_url: HttpUrl
    user: str


class ServiceNowTable(BaseModel):
    name: str
    label: Optional[str] = None


class ServiceNowTableListResponse(BaseModel):
    ok: bool
    tables: List[ServiceNowTable]
    returned: int


# ---------- Mappings ----------
class CreateMappingRequest(BaseModel):
    github_repo_full_name: str = Field(min_length=3, max_length=300, description="owner/repo")
    servicenow_table: str = Field(min_length=1, max_length=200)
    label: str = Field(default="default", max_length=100)


class MappingResponse(BaseModel):
    id: int
    github_repo_full_name: str
    servicenow_table: str
    label: str
    created_at: str


class MappingListResponse(BaseModel):
    ok: bool
    items: List[MappingResponse]


# ---------- Integrations (generic) ----------
class IntegrationSummary(BaseModel):
    id: int
    provider: str
    label: str
    config: dict
    created_at: str
    updated_at: str
    last_tested_at: Optional[str] = None
    last_test_ok: Optional[bool] = None
    last_test_message: Optional[str] = None


class IntegrationListResponse(BaseModel):
    ok: bool
    items: List[IntegrationSummary]


class DeleteResponse(BaseModel):
    ok: bool


# ---------- User settings ----------
class UserSettings(BaseModel):
    theme: str = Field(default="dark")
    notifications: bool = Field(default=True)


class UserSettingsResponse(BaseModel):
    ok: bool
    settings: UserSettings


class UpdateUserSettingsRequest(BaseModel):
    theme: Optional[str] = None
    notifications: Optional[bool] = None
