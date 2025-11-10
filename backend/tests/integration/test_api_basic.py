import os
import requests


def test_health(base_url: str):
    url = f"{base_url}/health"
    resp = requests.get(url, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_auth_health(base_url: str):
    # auth router mounts /digital_twin/research_chat/api/auth/health
    url = f"{base_url}/auth/health"
    resp = requests.get(url, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_login_and_get_sessions(base_url: str, auth_headers: dict):
    # basic list sessions with auth
    url = f"{base_url}/sessions?page=1&size=20"
    resp = requests.get(url, headers=auth_headers, timeout=20)
    # It might still return 200 with wrapped ErrorResponse
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, dict)
    # accept either success wrapper or raw list
    if "code" in data and "data" in data:
        assert data["code"] == 200
    # No strict schema checks to keep resilient to backend changes
