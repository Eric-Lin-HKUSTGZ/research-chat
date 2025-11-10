import asyncio
import types

import pytest
from starlette.testclient import TestClient

from app import main as app_main


class DummyCallNext:
    def __init__(self, response_headers=None, status_code=200):
        class Resp:
            def __init__(self, headers, status_code):
                self.headers = {**(headers or {})}
                self.status_code = status_code
        self._resp = Resp(response_headers, status_code)
    async def __call__(self, request):
        return self._resp


class DummyRequest:
    def __init__(self, path="/x", headers=None):
        class _URL:
            def __init__(self, path):
                self.path = path
        self.url = _URL(path)
        self.headers = headers or {}
        class _State:
            pass
        self.state = _State()


def test_middleware_adds_trace_headers_via_client():
    app = app_main.create_app()
    client = TestClient(app)
    resp = client.get("/")
    # middleware should add these headers
    assert "X-Request-Id" in resp.headers
    assert "X-Trace-Id" in resp.headers
    assert "X-Process-Time" in resp.headers


def test_root_and_health_routes():
    app = app_main.create_app()
    # directly call route handlers defined in create_app
    # root
    root_handler = None
    health_handler = None
    for r in app.router.routes:
        if getattr(r, "path", None) == "/":
            root_handler = r.endpoint
        if getattr(r, "path", None) == "/health":
            health_handler = r.endpoint
    assert root_handler and health_handler

    root = asyncio.run(root_handler())
    assert root["service"]
    health = asyncio.run(health_handler())
    assert health["status"] == "healthy"


def test_global_exception_handler(monkeypatch):
    app = app_main.create_app()
    handler = None
    for k, v in app.exception_handlers.items():
        if getattr(k, "__name__", "") == "Exception":
            handler = v
    assert handler is not None

    class Boom(Exception):
        pass

    # FastAPI passes request and exception; our handler returns JSONResponse-like object
    req = types.SimpleNamespace()
    out = asyncio.run(handler(req, Boom("x")))
    # JSONResponse has status_code and body
    assert getattr(out, "status_code", None) == 500
