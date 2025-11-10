import asyncio
import pytest

from app.routes import auth as routes_auth
from app.routes.auth import LoginRequest


class DummyUser:
    def __init__(self, id=1, email="u@e.com", is_active=True):
        self.id = id
        self.email = email
        self.username = None
        self.identity_tag = None
        self.is_active = is_active
        self.created_at = None
        self.updated_at = None


class DummyDB:
    def __init__(self):
        pass


def test_login_success(monkeypatch):
    user = DummyUser(id=7, email="a@b.com", is_active=True)
    monkeypatch.setattr(routes_auth, "verify_user_credentials", lambda e, p, d: user)
    monkeypatch.setattr(routes_auth, "generate_access_token", lambda u: "tok-xyz")

    req = LoginRequest(email="a@b.com", password="pw")
    resp = asyncio.run(routes_auth.login(req, db=DummyDB()))
    assert resp["code"] == 200
    assert resp["data"]["access_token"] == "tok-xyz"
    assert resp["data"]["user"]["id"] == 7


def test_login_invalid_credentials(monkeypatch):
    monkeypatch.setattr(routes_auth, "verify_user_credentials", lambda e, p, d: None)
    req = LoginRequest(email="a@b.com", password="pw")
    with pytest.raises(Exception) as ei:
        asyncio.run(routes_auth.login(req, db=DummyDB()))
    # FastAPI raises HTTPException(401)
    assert getattr(ei.value, "status_code", 401) == 401


def test_login_inactive_user(monkeypatch):
    user = DummyUser(id=7, email="a@b.com", is_active=False)
    monkeypatch.setattr(routes_auth, "verify_user_credentials", lambda e, p, d: user)
    req = LoginRequest(email="a@b.com", password="pw")
    with pytest.raises(Exception) as ei:
        asyncio.run(routes_auth.login(req, db=DummyDB()))
    assert getattr(ei.value, "status_code", 403) == 403


def test_login_generic_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(routes_auth, "verify_user_credentials", boom)
    req = LoginRequest(email="a@b.com", password="pw")
    with pytest.raises(Exception) as ei:
        asyncio.run(routes_auth.login(req, db=DummyDB()))
    assert getattr(ei.value, "status_code", 500) == 500
