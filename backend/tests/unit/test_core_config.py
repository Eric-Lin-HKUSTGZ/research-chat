import os
import re
import importlib
import types
import pytest

from app.core import config as config_module
from app.core.config import get_jwt_config, Config


def test_get_jwt_config_defaults(monkeypatch):
    # Ensure env not set so defaults from Config are used
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    cfg = get_jwt_config()
    assert set(cfg.keys()) == {"secret_key", "expires", "algorithm"}
    assert isinstance(cfg["secret_key"], str)
    assert isinstance(cfg["expires"], int)
    assert isinstance(cfg["algorithm"], str)
    assert cfg["expires"] > 0


def test_get_jwt_config_env_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret")
    cfg = get_jwt_config()
    assert cfg["secret_key"] == "unit-test-secret"


def test_get_jwt_config_algorithm_and_expires_int(monkeypatch):
    # Override class attributes safely
    monkeypatch.setattr(Config, "JWT_ALGORITHM", "HS512", raising=True)
    monkeypatch.setattr(Config, "JWT_ACCESS_TOKEN_EXPIRES", 3600, raising=True)

    cfg = get_jwt_config()
    assert cfg["algorithm"] == "HS512"
    assert cfg["expires"] == 3600


def test_get_jwt_config_bad_expires_fallback(monkeypatch):
    # If expires is not timedelta/int, fallback to 1 day
    monkeypatch.setattr(Config, "JWT_ACCESS_TOKEN_EXPIRES", "bad", raising=True)
    cfg = get_jwt_config()
    # 1 day in seconds
    assert 86400 - 5 <= cfg["expires"] <= 86400 + 5
