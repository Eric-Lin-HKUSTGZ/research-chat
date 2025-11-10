import re
from app.core.config import get_jwt_config, Config
from app.utils.error_handler import ErrorResponse
from app.services.auth import md5_hash


def test_get_jwt_config_types():
    cfg = get_jwt_config()
    assert set(cfg.keys()) == {"secret_key", "expires", "algorithm"}
    assert isinstance(cfg["secret_key"], str)
    assert isinstance(cfg["expires"], int)
    assert isinstance(cfg["algorithm"], str)


def test_error_response_success_and_error():
    ok = ErrorResponse.success_response("OK", {"a": 1})
    assert ok["code"] == 200
    assert ok["message"] == "OK"
    assert ok["data"] == {"a": 1}

    err = ErrorResponse.create_error_code_response(404, "not found")
    assert err["code"] == 404
    assert err["message"] == "not found"


def test_md5_hash_deterministic():
    a = md5_hash("abc")
    b = md5_hash("abc")
    c = md5_hash("abd")
    assert a == b
    assert a != c
    assert re.fullmatch(r"[0-9a-f]{32}", a)
