from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from systemlab_backend.main import create_app


def client_for(settings, fake_services):
    auth, repository = fake_services
    app = create_app(settings, analysis_repository=repository, auth_service=auth)
    return TestClient(app), auth, repository


def test_health_and_readiness(settings, fake_services) -> None:
    client, _, _ = client_for(settings, fake_services)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_analysis_endpoints_require_bearer_token(settings, fake_services) -> None:
    client, _, _ = client_for(settings, fake_services)
    response = client.get("/api/v1/analyses")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_create_list_and_get_analysis(settings, fake_services) -> None:
    client, _, repository = client_for(settings, fake_services)
    headers = {"Authorization": "Bearer valid-token"}
    response = client.post(
        "/api/v1/analyses",
        headers=headers,
        json={"repository_url": "https://github.com/owner/repository"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert client.get("/api/v1/analyses?limit=50&offset=0", headers=headers).status_code == 200
    assert client.get(f"/api/v1/analyses/{repository.analysis_id}", headers=headers).status_code == 200


def test_cross_user_analysis_is_hidden_as_404(settings, fake_services) -> None:
    client, _, _ = client_for(settings, fake_services)
    response = client.get(f"/api/v1/analyses/{uuid4()}", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 404


def test_artifact_not_ready_and_active_delete(settings, fake_services) -> None:
    client, _, repository = client_for(settings, fake_services)
    headers = {"Authorization": "Bearer valid-token"}
    graph = client.get(f"/api/v1/analyses/{repository.analysis_id}/graph", headers=headers)
    deletion = client.delete(f"/api/v1/analyses/{repository.analysis_id}", headers=headers)
    assert graph.status_code == 409
    assert graph.json()["detail"]["code"] == "ANALYSIS_NOT_READY"
    assert deletion.status_code == 409


def test_terminal_artifact_and_delete(settings, fake_services) -> None:
    client, _, repository = client_for(settings, fake_services)
    repository.status = "COMPLETED"
    headers = {"Authorization": "Bearer valid-token"}
    assert client.get(f"/api/v1/analyses/{repository.analysis_id}/graph", headers=headers).json() == {"nodes": []}
    assert client.delete(f"/api/v1/analyses/{repository.analysis_id}", headers=headers).status_code == 204


def test_oauth_refresh_me_and_logout_cookie_contract(settings, fake_services) -> None:
    client, auth, _ = client_for(settings, fake_services)
    begin = client.get("/api/v1/auth/github", follow_redirects=False)
    assert begin.status_code == 302
    assert "HttpOnly" in begin.headers["set-cookie"]
    assert begin.headers["cache-control"] == "private, no-store"

    client.cookies.set(settings.oauth_cookie_name, "signed-flow")
    callback = client.get("/api/v1/auth/callback?code=code", follow_redirects=False)
    assert callback.status_code == 303
    assert "refresh-token" in callback.headers["set-cookie"]

    client.cookies.set(settings.refresh_cookie_name, "refresh-token")
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.json()["access_token"] == "access-token"
    assert "rotated-token" in refreshed.headers["set-cookie"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert me.status_code == 200
    assert me.headers["cache-control"] == "private, no-store"

    logged_out = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert logged_out.status_code == 204
    assert auth.logout_args[0] == "valid-token"
