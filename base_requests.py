from __future__ import annotations

from typing import Dict, List, Optional, Literal
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


class GithubRepoDetails(BaseModel):
    id: int
    full_name: str
    private: bool
    html_url: HttpUrl
    description: Optional[str] = None
    default_branch: Optional[str] = None
    clone_url: Optional[HttpUrl] = None
    ssh_url: Optional[str] = None
    language: Optional[str] = None
    topics: Optional[List[str]] = None
    visibility: Optional[str] = None
    archived: Optional[bool] = None
    disabled: Optional[bool] = None
    fork: Optional[bool] = None
    stargazers_count: Optional[int] = None
    watchers_count: Optional[int] = None
    forks_count: Optional[int] = None
    open_issues_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pushed_at: Optional[str] = None
    owner_login: Optional[str] = None


class GithubRepoDetailsResponse(BaseModel):
    ok: bool
    repo: GithubRepoDetails


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


class ServiceNowField(BaseModel):
    name: str
    label: Optional[str] = None
    mandatory: bool = False
    type: Optional[str] = None
    reference: Optional[str] = None
    max_length: Optional[int] = None


class ServiceNowFieldListResponse(BaseModel):
    ok: bool
    table: str
    fields: List[ServiceNowField]
    returned: int


class ServiceNowRecordUpsertRequest(BaseModel):
    table: str = Field(min_length=1, max_length=200)
    data: Dict[str, object] = Field(..., min_items=1, description="Field/value pairs to send to ServiceNow")
    sys_id: Optional[str] = Field(default=None, max_length=100, description="If provided, record will be updated")
    label: str = Field(default="default", max_length=100)


class ServiceNowRecordResponse(BaseModel):
    ok: bool
    table: str
    sys_id: str
    action: str
    record: Dict[str, object]


# ---------- Mappings ----------
class CreateMappingRequest(BaseModel):
    github_repo_full_name: str = Field(min_length=3, max_length=300, description="owner/repo")
    servicenow_table: str = Field(min_length=1, max_length=200)
    label: str = Field(default="default", max_length=100)
    direction: Literal["github_to_servicenow", "servicenow_to_github", "bidirectional"] = Field(default="bidirectional")
    field_mapping: Optional[Dict[str, str]] = Field(default=None, description="Map of ServiceNow field -> GitHub field")


class MappingValidationRequest(BaseModel):
    github_repo_full_name: str = Field(min_length=3, max_length=300, description="owner/repo")
    servicenow_table: str = Field(min_length=1, max_length=200)
    label: str = Field(default="default", max_length=100)
    direction: Literal["github_to_servicenow", "servicenow_to_github", "bidirectional"] = Field(default="bidirectional")
    field_mapping: Dict[str, str] = Field(default_factory=dict, description="Map of ServiceNow field -> GitHub field")


class MappingValidationResponse(BaseModel):
    ok: bool
    suggested_mapping: Dict[str, str]
    missing_servicenow_fields: List[str]
    missing_github_fields: List[str]
    warnings: List[str]


class AutoMappingRequest(BaseModel):
    github_repo_full_name: str = Field(min_length=3, max_length=300, description="owner/repo")
    servicenow_table: str = Field(min_length=1, max_length=200)
    label: str = Field(default="default", max_length=100)
    direction: Literal["github_to_servicenow", "servicenow_to_github", "bidirectional"] = Field(default="bidirectional")


class AutoMappingResponse(BaseModel):
    ok: bool
    mapping: Dict[str, str]
    notes: List[str]


class MappingResponse(BaseModel):
    id: int
    github_repo_full_name: str
    servicenow_table: str
    label: str
    direction: str
    field_mapping: Dict[str, str]
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
