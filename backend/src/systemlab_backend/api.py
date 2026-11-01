from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from .auth import AuthenticatedUser, AuthService, bearer_token
from .errors import AuthenticationError
from .models import (
    AnalysisCreateRequest,
    AnalysisListResponse,
    AnalysisSummary,
    TokenResponse,
    UserResponse,
)
from .repositories import AnalysisRepository


router = APIRouter()


def repository(request: Request) -> AnalysisRepository:
    return request.app.state.analysis_repository


def auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def current_user(
    request: Request,
    auth: Annotated[AuthService, Depends(auth_service)],
) -> AuthenticatedUser:
    return auth.authenticate(bearer_token(request))  # type: ignore[arg-type]


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]
Repository = Annotated[AnalysisRepository, Depends(repository)]
Auth = Annotated[AuthService, Depends(auth_service)]


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


def analysis_summary(row: dict[str, Any]) -> AnalysisSummary:
    public_fields = AnalysisSummary.model_fields
    return AnalysisSummary.model_validate({key: value for key, value in row.items() if key in public_fields})


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(repo: Repository, response: Response) -> dict[str, str]:
    if not repo.ready():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ready"}


@router.get("/api/v1/auth/github")
def github_auth(auth: Auth) -> RedirectResponse:
    url, signed_flow = auth.begin_github_oauth()
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    auth.set_oauth_cookie(response, signed_flow)
    no_store(response)
    return response


@router.get("/api/v1/auth/callback")
def github_callback(request: Request, code: str, auth: Auth) -> RedirectResponse:
    signed_flow = request.cookies.get(auth.settings.oauth_cookie_name)
    if not signed_flow:
        raise AuthenticationError("The OAuth flow cookie is missing.")
    session = auth.finish_github_oauth(code, signed_flow)
    response = RedirectResponse(auth.settings.frontend_callback_url, status_code=status.HTTP_303_SEE_OTHER)
    auth.set_refresh_cookie(response, session.refresh_token)
    auth.clear_oauth_cookie(response)
    no_store(response)
    return response


@router.post("/api/v1/auth/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, auth: Auth) -> TokenResponse:
    refresh_token = request.cookies.get(auth.settings.refresh_cookie_name)
    if not refresh_token:
        raise AuthenticationError("The refresh cookie is missing.")
    token_response, rotated_refresh_token = auth.refresh(refresh_token)
    auth.set_refresh_cookie(response, rotated_refresh_token)
    no_store(response)
    return token_response


@router.get("/api/v1/auth/me", response_model=UserResponse)
def me(user: CurrentUser, response: Response) -> UserResponse:
    no_store(response)
    return user.response()


@router.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, auth: Auth) -> None:
    auth.logout(
        bearer_token(request, required=False),
        request.cookies.get(auth.settings.refresh_cookie_name),
    )
    auth.clear_refresh_cookie(response)
    no_store(response)


@router.post(
    "/api/v1/analyses",
    response_model=AnalysisSummary,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis(payload: AnalysisCreateRequest, user: CurrentUser, repo: Repository) -> AnalysisSummary:
    return analysis_summary(repo.create_and_enqueue(user.id, payload.repository_url))


@router.get("/api/v1/analyses", response_model=AnalysisListResponse)
def list_analyses(
    user: CurrentUser,
    repo: Repository,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AnalysisListResponse:
    rows = repo.list_for_user(user.id, limit, offset)
    return AnalysisListResponse(
        items=[analysis_summary(row) for row in rows],
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisSummary)
def get_analysis(analysis_id: UUID, user: CurrentUser, repo: Repository) -> AnalysisSummary:
    return analysis_summary(repo.get_for_user(user.id, analysis_id))


@router.get("/api/v1/analyses/{analysis_id}/graph")
def get_graph(analysis_id: UUID, user: CurrentUser, repo: Repository) -> dict[str, Any]:
    return repo.get_artifact_for_user(user.id, analysis_id, "graph")


@router.get("/api/v1/analyses/{analysis_id}/report")
def get_report(analysis_id: UUID, user: CurrentUser, repo: Repository) -> dict[str, Any]:
    return repo.get_artifact_for_user(user.id, analysis_id, "report")


@router.get("/api/v1/analyses/{analysis_id}/errors")
def get_errors(analysis_id: UUID, user: CurrentUser, repo: Repository) -> dict[str, Any]:
    return repo.get_artifact_for_user(user.id, analysis_id, "errors")


@router.delete("/api/v1/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: UUID, user: CurrentUser, repo: Repository) -> None:
    repo.delete_for_user(user.id, analysis_id)
