from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from base_requests import (
    RegisterRequest, LoginRequest, TokenResponse, MeResponse, UpdateMeRequest, ChangePasswordRequest,
    GithubConnectRequest, GithubConnectResponse, GithubRepoListResponse,
    GithubRepoDetailsResponse,
    ServiceNowConnectRequest, ServiceNowConnectResponse, ServiceNowTableListResponse,
    ServiceNowFieldListResponse, ServiceNowRecordUpsertRequest, ServiceNowRecordResponse,
    CreateMappingRequest, MappingResponse, MappingListResponse,
    MappingValidationRequest, MappingValidationResponse, AutoMappingRequest, AutoMappingResponse,
    IntegrationListResponse, DeleteResponse,
    UserSettingsResponse, UpdateUserSettingsRequest,
    HealthResponse,
)
from service_impl.auth_service import AuthService
from service_impl.github_service import GithubService
from service_impl.servicenow_service import ServiceNowService
from service_impl.mapping_service import MappingService
from service_impl.integration_service import IntegrationService
from service_impl.user_settings_service import UserSettingsService
from impl.security.deps import get_current_user


router = APIRouter(prefix="/api", tags=["platform"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True)


# ---------- Auth ----------
@router.post("/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest) -> TokenResponse:
    return AuthService().register(req)


@router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    # JSON login for your frontend
    return AuthService().login(req)


@router.post("/auth/token", response_model=TokenResponse)
def token(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    # OAuth2 form login (Swagger "Authorize" button uses this)
    return AuthService().login_password(email=form.username, password=form.password)


@router.get("/auth/me", response_model=MeResponse)
def me(user=Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, created_at=user.created_at.isoformat())


@router.patch("/auth/me", response_model=MeResponse)
def update_me(req: UpdateMeRequest, user=Depends(get_current_user)) -> MeResponse:
    return AuthService().update_me(user_id=user.id, req=req)


@router.post("/auth/change-password", response_model=DeleteResponse)
def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)) -> DeleteResponse:
    AuthService().change_password(user_id=user.id, req=req)
    return DeleteResponse(ok=True)


# ---------- User settings ----------
@router.get("/user/settings", response_model=UserSettingsResponse)
def get_settings(user=Depends(get_current_user)) -> UserSettingsResponse:
    return UserSettingsService().get(user_id=user.id)


@router.put("/user/settings", response_model=UserSettingsResponse)
def put_settings(req: UpdateUserSettingsRequest, user=Depends(get_current_user)) -> UserSettingsResponse:
    return UserSettingsService().update(user_id=user.id, req=req)


# ---------- Integrations (generic) ----------
@router.get("/integrations", response_model=IntegrationListResponse)
def list_integrations(user=Depends(get_current_user)) -> IntegrationListResponse:
    return IntegrationService().list(user_id=user.id)


@router.delete("/integrations/{provider}/{label}", response_model=DeleteResponse)
def delete_integration(provider: str, label: str, user=Depends(get_current_user)) -> DeleteResponse:
    IntegrationService().delete(user_id=user.id, provider=provider, label=label)
    return DeleteResponse(ok=True)


# ---------- Integrations: GitHub ----------
@router.put("/integrations/github", response_model=GithubConnectResponse)
def connect_github(req: GithubConnectRequest, user=Depends(get_current_user)) -> GithubConnectResponse:
    return GithubService().connect(user_id=user.id, req=req)


@router.get("/github/repos", response_model=GithubRepoListResponse)
def list_github_repos(label: str = "default", user=Depends(get_current_user)) -> GithubRepoListResponse:
    return GithubService().list_repos(user_id=user.id, label=label)


@router.get("/github/repo", response_model=GithubRepoDetailsResponse)
def github_repo_details(full_name: str, label: str = "default", user=Depends(get_current_user)) -> GithubRepoDetailsResponse:
    return GithubService().get_repo_details(user_id=user.id, full_name=full_name, label=label)


# ---------- Integrations: ServiceNow ----------
@router.put("/integrations/servicenow", response_model=ServiceNowConnectResponse)
def connect_servicenow(req: ServiceNowConnectRequest, user=Depends(get_current_user)) -> ServiceNowConnectResponse:
    return ServiceNowService().connect(user_id=user.id, req=req)


@router.get("/servicenow/tables", response_model=ServiceNowTableListResponse)
def list_servicenow_tables(
    limit: int = 50,
    query: str | None = None,
    label: str = "default",
    user=Depends(get_current_user),
) -> ServiceNowTableListResponse:
    return ServiceNowService().list_tables(user_id=user.id, limit=limit, query=query, label=label)


@router.get("/servicenow/{table}/fields", response_model=ServiceNowFieldListResponse)
def list_servicenow_fields(
    table: str,
    label: str = "default",
    user=Depends(get_current_user),
) -> ServiceNowFieldListResponse:
    return ServiceNowService().list_fields(user_id=user.id, table=table, label=label)


@router.post("/servicenow/records", response_model=ServiceNowRecordResponse)
def upsert_servicenow_record(req: ServiceNowRecordUpsertRequest, user=Depends(get_current_user)) -> ServiceNowRecordResponse:
    return ServiceNowService().upsert_record(user_id=user.id, req=req)


# ---------- Mappings ----------
@router.post("/mappings", response_model=MappingResponse)
def create_mapping(req: CreateMappingRequest, user=Depends(get_current_user)) -> MappingResponse:
    return MappingService().create(user_id=user.id, req=req)


@router.get("/mappings", response_model=MappingListResponse)
def list_mappings(user=Depends(get_current_user)) -> MappingListResponse:
    return MappingService().list(user_id=user.id)


@router.post("/mappings/validate", response_model=MappingValidationResponse)
def validate_mapping(req: MappingValidationRequest, user=Depends(get_current_user)) -> MappingValidationResponse:
    return MappingService().validate(user_id=user.id, req=req)


@router.post("/mappings/auto", response_model=AutoMappingResponse)
def auto_map(req: AutoMappingRequest, user=Depends(get_current_user)) -> AutoMappingResponse:
    return MappingService().auto_map(user_id=user.id, req=req)
