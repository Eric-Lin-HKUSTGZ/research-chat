import asyncio
import pytest
from fastapi import HTTPException

from app.services import auth as auth_mod
from app.services.auth import get_current_user, verify_user_credentials, generate_access_token, JWTManager


class DummyUser:
    def __init__(self, id=1, email="u@e.com", is_active=True):
        self.id = id
        self.email = email
        self.is_active = is_active
        self.username = None
        self.identity_tag = None
        self.created_at = None
        self.updated_at = None


class DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class DummyDB:
    def __init__(self, value):
        self._value = value

    def execute(self, query):  # query ignored for unit test
        return DummyResult(self._value)


def test_get_current_user_no_header_raises():
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user(authorization=None, db=None))
    assert ei.value.status_code == 401
    assert ei.value.headers.get("WWW-Authenticate") == "Bearer"


def test_get_current_user_bad_format_raises():
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user(authorization="Basic abc", db=None))
    assert ei.value.status_code == 401


def test_get_current_user_invalid_token_raises(monkeypatch):
    monkeypatch.setattr(auth_mod.jwt_manager, "decode_token", lambda t: None)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user(authorization="Bearer x", db=DummyDB(None)))
    assert ei.value.status_code == 401


def test_get_current_user_missing_fields_raises(monkeypatch):
    monkeypatch.setattr(auth_mod.jwt_manager, "decode_token", lambda t: {"user_id": None, "email": "e"})
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user(authorization="Bearer x", db=DummyDB(None)))
    assert ei.value.status_code == 401


def test_get_current_user_user_not_found_raises(monkeypatch):
    monkeypatch.setattr(auth_mod.jwt_manager, "decode_token", lambda t: {"user_id": 1, "email": "e"})
    # DB returns None -> user not found
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user(authorization="Bearer x", db=DummyDB(None)))
    assert ei.value.status_code == 401


def test_get_current_user_success(monkeypatch):
    monkeypatch.setattr(auth_mod.jwt_manager, "decode_token", lambda t: {"user_id": 1, "email": "e"})
    user = DummyUser(id=1, email="e", is_active=True)
    out = asyncio.run(get_current_user(authorization="Bearer x", db=DummyDB(user)))
    assert out == {"user_id": 1, "email": "e"}


def test_verify_user_credentials_success(monkeypatch):
    user = DummyUser(email="e")
    db = DummyDB(user)
    out = verify_user_credentials("e", "pw", db)
    assert out is user


def test_verify_user_credentials_failure(monkeypatch):
    db = DummyDB(None)
    out = verify_user_credentials("e", "pw", db)
    assert out is None


def test_generate_access_token(monkeypatch):
    # monkeypatch global jwt_manager
    monkeypatch.setattr(auth_mod.jwt_manager, "generate_token", lambda uid, email: "tok-123")
    user = DummyUser(id=5, email="ee")
    tok = generate_access_token(user)
    assert tok == "tok-123"


def test_jwtmanager_decode_generic_exception(monkeypatch):
    mgr = JWTManager()

    def boom(*a, **k):
        raise ValueError("bad")

    import jwt as pyjwt

    monkeypatch.setattr(pyjwt, "decode", boom)
    assert mgr.decode_token("whatever") is None
