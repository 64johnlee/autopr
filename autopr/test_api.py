"""Hermetic tests for the AutoPR REST API (no network / API keys needed)."""
from fastapi.testclient import TestClient

from autopr.api_server import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_open_pr_unknown_session_fails_gracefully():
    r = client.post("/open_pr", json={"session_id": "nope"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert "session" in body["error"]


def test_discard_unknown_session_fails_gracefully():
    r = client.post("/discard", json={"session_id": "nope"})
    assert r.json()["success"] is False


def test_missing_body_is_422():
    assert client.post("/open_pr", json={}).status_code == 422


def test_bearer_auth_enforced_when_token_set(monkeypatch):
    monkeypatch.setenv("AUTOPR_API_TOKEN", "secret")
    # no header → rejected
    assert client.post("/discard", json={"session_id": "x"}).status_code == 401
    # wrong token → rejected
    assert client.post("/discard", json={"session_id": "x"},
                       headers={"Authorization": "Bearer wrong"}).status_code == 401
    # correct token → allowed through to the handler
    ok = client.post("/discard", json={"session_id": "x"},
                     headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200


def test_no_auth_required_when_token_unset(monkeypatch):
    monkeypatch.delenv("AUTOPR_API_TOKEN", raising=False)
    assert client.post("/discard", json={"session_id": "x"}).status_code == 200
