import types
import pytest

import requests

from app.services.llm_service import get_newest_paper, get_highly_cited_paper, get_relevence_paper


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_get_newest_paper_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResp({"data": [{"title": "t", "abstract": "a"}, {"title": "t2", "abstract": "a2"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    out = get_newest_paper("q", max_results=1, max_retries=1)
    assert out == [{"title": "t", "abstract": "a"}]


def test_get_newest_paper_retry_then_empty(monkeypatch):
    seq = [DummyResp({}), DummyResp({})]

    def fake_get(url, params=None, timeout=None):
        return seq.pop(0)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)
    out = get_newest_paper("q", max_results=1, max_retries=2)
    assert out == []


def test_get_highly_cited_paper_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResp({"data": [{"title": "t" + params.get("sort", ""), "abstract": "a"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    out = get_highly_cited_paper("q", max_results=1, max_retries=1)
    assert out and "title" in out[0]


def test_get_relevence_paper_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResp({"data": [{"title": "t3", "abstract": "a3"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    out = get_relevence_paper("q", max_results=1, max_retries=1)
    assert out == [{"title": "t3", "abstract": "a3"}]
