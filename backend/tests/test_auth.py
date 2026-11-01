from fastapi.testclient import TestClient

from tests.conftest import EMAIL, PASSWORD


def test_me_requires_session(anon: TestClient) -> None:
    r = anon.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json() == {"code": "unknown", "message": "Not signed in. Sign in to continue."}


def test_protected_routes_require_session(anon: TestClient) -> None:
    for path in ("/api/documents", "/api/conversations", "/api/usage"):
        assert anon.get(path).status_code == 401, path
    assert anon.post("/api/conversations").status_code == 401


def test_wrong_password(anon: TestClient) -> None:
    r = anon.post("/api/auth/login", json={"email": EMAIL, "password": "nope"})
    assert r.status_code == 401
    assert r.json()["message"] == "That email and password combination is incorrect."
    r = anon.post("/api/auth/login", json={"email": "someone@else.com", "password": PASSWORD})
    assert r.status_code == 401


def test_login_me_logout(anon: TestClient) -> None:
    r = anon.post("/api/auth/login", json={"email": EMAIL.upper(), "password": PASSWORD})
    assert r.status_code == 200
    assert set(r.json()) == {"id", "name", "email", "initials"}
    assert r.json()["initials"] == "DW"
    cookie = r.headers["set-cookie"]
    assert "ll_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie

    assert anon.get("/api/auth/me").json()["email"] == EMAIL
    assert anon.post("/api/auth/logout").status_code == 204
    anon.cookies.clear()
    assert anon.get("/api/auth/me").status_code == 401


def test_logout_invalidates_server_side(anon: TestClient) -> None:
    anon.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    token = anon.cookies.get("ll_session")
    anon.post("/api/auth/logout")
    anon.cookies.set("ll_session", token)  # replaying the old cookie must not work
    assert anon.get("/api/auth/me").status_code == 401


def test_login_rate_limited(anon: TestClient) -> None:
    for _ in range(5):
        assert anon.post("/api/auth/login", json={"email": EMAIL, "password": "x"}).status_code == 401
    r = anon.post("/api/auth/login", json={"email": EMAIL, "password": "x"})
    assert r.status_code == 429
    body = r.json()
    assert body["code"] == "rate_limited" and body["retryAfterSec"] >= 1
    assert r.headers["retry-after"] == str(body["retryAfterSec"])


def test_validation_error_envelope(anon: TestClient) -> None:
    r = anon.post("/api/auth/login", json={"email": EMAIL})
    assert r.status_code == 422
    assert r.json()["code"] == "unknown"
    assert "password" in r.json()["message"]


def test_request_id_echoed(anon: TestClient) -> None:
    r = anon.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    assert anon.get("/api/health").headers["x-request-id"].startswith("req_")
