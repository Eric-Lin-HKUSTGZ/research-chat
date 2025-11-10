import os, sys, json, ast
import pytest
import requests
from dotenv import load_dotenv
from collections import defaultdict

# ======== Path + dotenv ========
# Allow importing project code and load test-specific .env
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(os.path.abspath(os.path.join(HERE, "..")), ".env"))

# ======== Warning filters (test-only) ========
import warnings as _warnings
_warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"Using SQLAlchemy.*LegacyAPIWarning.*",
)
_warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r"Using the in-memory storage for tracking rate limits.*",
)

# ======== Basic config fixtures ========
@pytest.fixture(scope="session")
def base_url() -> str:
    """API base URL.
    Env priority: API_BASE_URL -> BASE_URL -> default local.
    """
    url = (
        os.getenv("API_BASE_URL")
        or os.getenv("BASE_URL")
        or "http://127.0.0.1:5000/digital_twin/research_chat/api"
    )
    return url.rstrip("/")

@pytest.fixture(scope="session")
def requests_session():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    try:
        yield s
    finally:
        s.close()

@pytest.fixture(scope="session")
def server_ready(base_url, requests_session):
    """Skip tests if the external API server isn't reachable."""
    try:
        r = requests_session.get(f"{base_url}/health", timeout=5)
        if r.status_code >= 500:
            pytest.skip(
                f"API server reachable but unhealthy (status={r.status_code}) at {base_url}"
            )
    except Exception as e:
        pytest.skip(f"API server not reachable at {base_url}: {e}")

@pytest.fixture(scope="session")
def auth_headers() -> dict:
    """Authorization header using Bearer token.
    Env priority: API_BEARER_TOKEN -> TOKEN. Accepts with/without 'Bearer ' prefix.
    If not provided, optional login using LOGIN_EMAIL/LOGIN_PASSWORD when BASE_URL allows.
    """
    token = os.getenv("API_BEARER_TOKEN", "").strip()
    if not token:
        token = os.getenv("TOKEN", "").strip()
    # If still empty, try login flow when creds are present
    if not token:
        email = os.getenv("LOGIN_EMAIL", "").strip()
        password = os.getenv("LOGIN_PASSWORD", "").strip()
        base = (
            os.getenv("API_BASE_URL")
            or os.getenv("BASE_URL")
            or "http://127.0.0.1:5000/digital_twin/research_chat/api"
        ).rstrip("/")
        if email and password:
            try:
                resp = requests.post(
                    f"{base}/auth/login",
                    json={"email": email, "password": password},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                # Accept either wrapped or flat token formats
                if isinstance(data, dict) and data.get("data") and data["data"].get("access_token"):
                    token = data["data"]["access_token"]
                elif isinstance(data, dict) and data.get("access_token"):
                    token = data["access_token"]
            except Exception:
                # Leave token empty; tests that require auth can skip via auth_ok
                token = ""
    if token and not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    return {"Authorization": token} if token else {}

@pytest.fixture(scope="session")
def auth_ok(base_url, requests_session, auth_headers) -> bool:
    """Probe an auth-required endpoint to determine if provided token works.
    If unauthorized or missing, auth-required tests can decide to skip.
    """
    if not auth_headers:
        return False
    try:
        r = requests_session.get(f"{base_url}/sessions", headers=auth_headers, timeout=5)
        if r.status_code == 200:
            try:
                body = r.json()
                # Accept either success wrapper or raw list
                return (isinstance(body, dict) and body.get("code") == 200) or isinstance(body, (list, dict))
            except Exception:
                return True
        return False
    except Exception:
        return False

# ======== Gate scheduler (silence shutdown noise) ========
@pytest.fixture(autouse=True, scope="session")
def _gate_scheduler():
    """Disable APScheduler during tests by no-op init_app."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    try:
        try:
            from backend.app.services.scheduler_service import scheduler_service as _inst
            mp.setattr(_inst.__class__, "init_app", lambda self, app: None, raising=True)
        except Exception:
            try:
                from backend.app.services import scheduler_service as _mod
                if hasattr(_mod, "scheduler_service"):
                    mp.setattr(_mod.scheduler_service.__class__, "init_app", lambda self, app: None, raising=True)
            except Exception:
                pass
        yield
    finally:
        mp.undo()

# ======== Keep runtime warning suppression ========
@pytest.fixture(autouse=True, scope="session")
def _suppress_deprecation_warnings():
    _warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"Using SQLAlchemy.*LegacyAPIWarning.*",
    )
    _warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=r"Using the in-memory storage for tracking rate limits.*",
    )

# ======== JUnit-like HTTP method summary (console + file) ========
_HTTP_SOURCES = {"requests", "requests_session", "session", "client", "httpx", "s", "test_client"}
_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")


def _infer_methods_from_file(file_path: str) -> dict[str, str]:
    """Return mapping of test func name -> HTTP method (or 'UNKNOWN')."""
    result: dict[str, str] = {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
        tree = ast.parse(src, filename=file_path)
    except Exception:
        return result

    def method_from_call(node: ast.Call) -> str | None:
        try:
            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                base = node.func.value
                if attr.lower() in {m.lower() for m in _HTTP_METHODS}:
                    if isinstance(base, ast.Name) and base.id in _HTTP_SOURCES:
                        return attr.upper()
                    if isinstance(base, ast.Attribute):
                        if base.attr in _HTTP_SOURCES:
                            return attr.upper()
                        if isinstance(base.value, ast.Name) and base.value.id == "self" and base.attr in _HTTP_SOURCES:
                            return attr.upper()
                if attr == "request":
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        m = node.args[0].value.upper()
                        if m in _HTTP_METHODS:
                            return m
                    for kw in node.keywords or []:
                        if kw.arg == "method" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                            m = kw.value.value.upper()
                            if m in _HTTP_METHODS:
                                return m
        except Exception:
            return None
        return None

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self._stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            push = node.name.startswith("test")
            if push:
                self._stack.append(node.name)
            self.generic_visit(node)
            if push:
                fname = self._stack.pop()
                result.setdefault(fname, "UNKNOWN")

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_FunctionDef(node)  # type: ignore[arg-type]

        def visit_Call(self, node: ast.Call) -> None:
            if self._stack:
                m = method_from_call(node)
                if m and result.get(self._stack[-1], "UNKNOWN") == "UNKNOWN":
                    result[self._stack[-1]] = m
            self.generic_visit(node)

    _Visitor().visit(tree)
    return result


def pytest_configure(config):
    if not hasattr(config, "_dt_store"):
        config._dt_store = {"reports": {}, "method_cache": {}}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    store = getattr(item.config, "_dt_store", None)
    if store is None:
        return

    nodeid = item.nodeid
    file_path = str(item.fspath)
    func_name = getattr(item, "name", None) or (
        getattr(item.function, "__name__", None) if hasattr(item, "function") else None
    ) or nodeid.split("::")[-1]

    status_map_rank = {"passed": 1, "skipped": 2, "failed": 3, "error": 4}
    if rep.outcome == "failed":
        status = "error" if rep.when in ("setup", "teardown") else "failed"
    else:
        status = rep.outcome

    rec = store["reports"].get(
        nodeid,
        {
            "nodeid": nodeid,
            "file": file_path,
            "func_name": func_name,
            "status": "passed",
            "time": 0.0,
        },
    )

    if status_map_rank.get(status, 0) >= status_map_rank.get(rec["status"], 0):
        rec["status"] = status
    try:
        rec["time"] = float(rec.get("time", 0.0)) + float(getattr(rep, "duration", 0.0) or 0.0)
    except Exception:
        pass

    store["reports"][nodeid] = rec


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    store = getattr(config, "_dt_store", None)
    if not store:
        return

    reports = list(store["reports"].values())
    if not reports:
        terminalreporter.write_line("<testsuites></testsuites>")
        return

    by_file: dict[str, list[dict]] = defaultdict(list)
    for r in reports:
        by_file[r["file"]].append(r)

    lines: list[str] = []
    lines.append("<testsuites>")
    method_order = list(_HTTP_METHODS) + ["UNKNOWN"]

    for file_path in sorted(by_file.keys()):
        cases = by_file[file_path]
        cache = store["method_cache"]
        if file_path not in cache:
            cache[file_path] = _infer_methods_from_file(file_path)
        idx: dict[str, str] = cache[file_path]

        total = len(cases)
        failures = sum(1 for c in cases if c["status"] == "failed")
        errors = sum(1 for c in cases if c["status"] == "error")
        skipped = sum(1 for c in cases if c["status"] == "skipped")

        lines.append(
            f"  <testsuite name=\"{file_path}\" tests=\"{total}\" failures=\"{failures}\" errors=\"{errors}\" skipped=\"{skipped}\">"
        )

        by_method: dict[str, list[dict]] = defaultdict(list)
        for c in cases:
            method = idx.get(c["func_name"], "UNKNOWN")
            by_method[method].append(c)

        for method in method_order:
            method_cases = by_method.get(method)
            if not method_cases:
                continue
            m_total = len(method_cases)
            m_fail = sum(1 for c in method_cases if c["status"] == "failed")
            m_err = sum(1 for c in method_cases if c["status"] == "error")
            m_skip = sum(1 for c in method_cases if c["status"] == "skipped")
            lines.append(
                f"    <testsuite name=\"{method}\" tests=\"{m_total}\" failures=\"{m_fail}\" errors=\"{m_err}\" skipped=\"{m_skip}\">"
            )
            for c in sorted(method_cases, key=lambda x: x["nodeid"]):
                t = f"{c.get('time', 0.0):.3f}"
                lines.append(
                    f"      <testcase name=\"{c['nodeid']}\" status=\"{c['status']}\" time=\"{t}\"/>"
                )
            lines.append("    </testsuite>")

        lines.append("  </testsuite>")

    lines.append("</testsuites>")

    for ln in lines:
        terminalreporter.write_line(ln)

    out_path = os.getenv(
        "PYTEST_HTTP_REPORT_PATH", os.path.join(os.getcwd(), "junit_http_summary.txt")
    )
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        terminalreporter.write_line(f"[http-report] Written grouped summary to: {out_path}")
    except Exception as e:
        terminalreporter.write_line(f"[http-report] Failed to write summary file: {e}")
