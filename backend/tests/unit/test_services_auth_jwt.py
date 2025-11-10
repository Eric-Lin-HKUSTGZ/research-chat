import time
from datetime import datetime, timedelta
import jwt
from app.utils.tools import UTC8

from app.services.auth import JWTManager, md5_hash


class DummyJWTManager(JWTManager):
    """Expose config overrides for testing"""

    def __init__(self, secret="s", algorithm="HS256", expires_seconds=2):
        self.config = {
            "secret_key": secret,
            "algorithm": algorithm,
            "expires": expires_seconds,
        }


def test_md5_hash_deterministic_and_hex():
    a = md5_hash("abc")
    b = md5_hash("abc")
    c = md5_hash("abd")
    assert a == b and a != c
    assert len(a) == 32 and all(ch in "0123456789abcdef" for ch in a)


def test_jwt_generate_and_decode_success():
    mgr = DummyJWTManager(secret="unit-secret", expires_seconds=60)
    tok = mgr.generate_token(user_id=123, email="u@e.com")
    payload = mgr.decode_token(tok)
    assert payload and payload["user_id"] == 123 and payload["email"] == "u@e.com"
    assert payload["type"] == "access"


def test_jwt_decode_invalid_type():
    mgr = DummyJWTManager(secret="unit-secret", expires_seconds=60)
    now = datetime.now(UTC8)
    bad_token = jwt.encode(
        {"user_id": 1, "email": "a@b.com", "iat": now, "exp": now + timedelta(seconds=60), "type": "refresh"},
        "unit-secret",
        algorithm="HS256",
    )
    assert mgr.decode_token(bad_token) is None


def test_jwt_decode_expired():
    mgr = DummyJWTManager(secret="unit-secret", expires_seconds=1)
    tok = mgr.generate_token(user_id=1, email="a@b.com")
    time.sleep(1.2)
    assert mgr.decode_token(tok) is None


def test_jwt_decode_invalid_signature():
    mgr = DummyJWTManager(secret="unit-secret", expires_seconds=60)
    tok = mgr.generate_token(user_id=1, email="a@b.com")
    # Corrupt the signature to force InvalidSignatureError
    tampered = tok[:-1] + ("A" if tok[-1] != "A" else "B")
    assert mgr.decode_token(tampered) is None
