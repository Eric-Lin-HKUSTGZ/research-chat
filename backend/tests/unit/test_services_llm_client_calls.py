import types

import pytest
import requests

from app.services.llm_service import LLMClient


class DummyResp:
    def __init__(self, payload=None):
        self._payload = payload or {
            "choices": [
                {"message": {"content": "ok"}}
            ]
        }

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_llm_client_get_response_success(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1
        return DummyResp()

    monkeypatch.setattr(requests, "post", fake_post)

    client = LLMClient(provider="custom")
    out = client.get_response("hello")
    assert out == "ok"
    assert calls["n"] == 1


def test_llm_client_timeout_then_success(monkeypatch):
    seq = [requests.exceptions.Timeout(), DummyResp()]

    def fake_post(url, headers=None, json=None, timeout=None):
        v = seq.pop(0)
        if isinstance(v, Exception):
            raise v
        return v

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)

    client = LLMClient(provider="custom")
    # Reduce retries to avoid long loops in case of failure
    client.max_retries = 2
    out = client.get_response("hello")
    assert out == "ok"


def test_llm_client_request_exception_raises(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)

    client = LLMClient(provider="custom")
    client.max_retries = 2
    with pytest.raises(Exception):
        client.get_response("hello")
