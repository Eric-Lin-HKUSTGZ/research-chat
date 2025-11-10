import asyncio
from datetime import datetime

import pytest

from app.routes import chat_routes as routes
from app.utils.error_handler import ErrorCode
from app.utils.tools import UTC8


class DummySession:
    def __init__(self, items=None, total=0, session=None, rows=None):
        self._items = items or []
        self._total = total
        self._session = session
        self._rows = rows or []
        self.executed = []
        self.commits = 0
        self.rollbacks = 0
        self.deletes = []
        self.added = []
        self.flushed = 0

    # emulate SQLAlchemy session API used in code
    def execute(self, stmt):
        self.executed.append(stmt)
        class _Res:
            def __init__(self, rows, items):
                self._rows = rows
                self._items = items
            def scalars(self):
                class _Sc:
                    def __init__(self, items):
                        self._items = items
                    def all(self):
                        return list(self._items)
                return _Sc(self._items)
            def first(self):
                return self._rows[0] if self._rows else None
            def all(self):
                return list(self._rows)
        return _Res(self._rows, self._items)

    def scalar(self, stmt):
        return self._session

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed += 1

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def delete(self, obj):
        self.deletes.append(obj)


@pytest.mark.parametrize("inp, exp", [
    (None, "page_"),
    ("abc", "abc"),
])

def test_generate_page_session_id(inp, exp):
    out = routes.generate_page_session_id(inp)
    assert out.startswith(exp)


def test_get_sessions_success(monkeypatch):
    now = datetime.now(UTC8)
    # fake items returned by scalars().all()
    item = type("S", (), {
        "id": 1, "page_session_id": "p1", "session_name": "n",
        "is_active": True, "created_at": now, "updated_at": now
    })()
    sess = DummySession(items=[item])

    # scalar total
    def fake_scalar(stmt):
        return 1
    sess.scalar = fake_scalar

    out = asyncio.run(routes.get_sessions(page=1, size=10, current_user={"user_id": 1}, db=sess))
    assert out["code"] == ErrorCode.SUCCESS.value
    data = out["data"]
    assert data["user_id"] == 1
    assert data["sessions"][0]["session_id"] == "p1"
    assert data["pagination"]["total"] == 1


def test_get_session_messages_no_session(monkeypatch):
    sess = DummySession(session=None)
    out = asyncio.run(routes.get_session_messages("sid", request=type("R", (), {"query_params": {}})(), current_user={"user_id": 1}, db=sess))
    assert out["code"] == 200
    assert out["data"] == []


def test_get_session_messages_latest(monkeypatch):
    now = datetime.now(UTC8)
    m = type("M", (), {
        "id": 3, "content": "q", "result_papers": None,
        "created_at": now, "updated_at": now
    })()
    p = type("P", (), {
        "id": 9, "creation_status": "creating", "process_info": {"logs": []},
        "created_at": now, "updated_at": now
    })()
    sess = DummySession(rows=[(m, p)], session=type("Sess", (), {"id": 1})())
    out = asyncio.run(routes.get_session_messages("sid", request=type("R", (), {"query_params": {"latest": "1"}})(), current_user={"user_id": 1}, db=sess))
    assert out["code"] == 200
    assert isinstance(out["data"], list)
    assert out["data"][0]["process"]["id"] == 9


def test_update_session_name_not_found(monkeypatch):
    sess = DummySession(session=None)
    out = asyncio.run(routes.update_session_name("sid", request=routes.UpdateSessionNameRequest(session_name="x"), current_user={"user_id": 1}, db=sess))
    assert out["code"] == ErrorCode.NOT_FOUND.value


def test_delete_session_success(monkeypatch):
    class Obj:
        pass
    obj = Obj()
    sess = DummySession(session=obj)
    out = asyncio.run(routes.delete_session("sid", current_user={"user_id": 1}, db=sess))
    assert out["code"] == 200
    assert sess.deletes == [obj]
    assert sess.commits == 1


def test_create_research_conflict(monkeypatch):
    # Existing in-progress task
    class S:
        id = 11
        page_session_id = "p1"
    class Proc:
        message_id = 99
    def fake_scalar(stmt):
        # First call for session lookup returns S(); second call for in-progress returns Proc(); others return None
        fake_scalar.calls += 1
        if fake_scalar.calls == 1:
            return S()
        if fake_scalar.calls == 2:
            return Proc()
        return None
    fake_scalar.calls = 0

    sess = DummySession()
    sess.scalar = fake_scalar
    resp = type("Resp", (), {"status_code": 200})()
    out = asyncio.run(routes.create_research(
        request=routes.CreateResearchRequest(content="hello", session_id="p1", locale="cn"),
        response=resp,
        x_page_id=None,
        background_tasks=None,
        current_user={"user_id": 1, "email": "e"},
        db=sess,
    ))
    assert resp.status_code == ErrorCode.CONFLICT.value
    assert out["code"] == ErrorCode.CONFLICT.value


# ===== New tests to cover remaining branches =====

def test_get_session_messages_pagination(monkeypatch):
    now = datetime.now(UTC8)
    # session exists
    session_obj = type("Sess", (), {"id": 1})()

    # prepare two rows (but our DummySession ignores offset/limit, we just ensure structure)
    m1 = type("M", (), {"id": 1, "content": "q1", "result_papers": None, "created_at": now, "updated_at": now})()
    p1 = type("P", (), {"id": 101, "creation_status": "creating", "process_info": {"logs": ["l1"]}, "created_at": now, "updated_at": now})()

    class SessForPagination(DummySession):
        def __init__(self):
            super().__init__(rows=[(m1, p1)])
            self._session_lookup_calls = 0
        def scalar(self, stmt):
            # First scalar -> session lookup; Second -> total count
            self._session_lookup_calls += 1
            if self._session_lookup_calls == 1:
                return session_obj
            return 3  # total messages

    sess = SessForPagination()
    req = type("R", (), {"query_params": {"page": "2", "size": "1"}})()
    out = asyncio.run(routes.get_session_messages("sid", request=req, current_user={"user_id": 1}, db=sess))
    assert out["code"] == 200
    data = out["data"]
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["size"] == 1
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["pages"] == 3
    assert isinstance(data["content"], list) and len(data["content"]) == 1
    assert data["content"][0]["process"]["id"] == 101


def test_create_research_new_session_and_background(monkeypatch):
    # Make generate_page_session_id deterministic
    monkeypatch.setattr(routes, 'generate_page_session_id', lambda x: 'new_session_id')

    class Bg:
        def __init__(self):
            self.calls = []
        def add_task(self, fn, *args):
            self.calls.append((fn, args))

    # Session that assigns IDs on add() and tracks flush/commit
    class Sess:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
            self.flushed = 0
            self.added = []
        def execute(self, stmt):
            class R:
                def first(self_inner):
                    return None
                def scalars(self_inner):
                    class _Sc:
                        def all(self):
                            return []
                    return _Sc()
            return R()
        def scalar(self, stmt):
            return None  # no in-progress task
        def add(self, obj):
            # Assign IDs similar to DB auto-increment
            if hasattr(obj, 'page_session_id') and getattr(obj, 'id', None) is None:
                obj.id = 10
            if hasattr(obj, 'content') and getattr(obj, 'id', None) is None:
                obj.id = 20
            if hasattr(obj, 'creation_status') and getattr(obj, 'id', None) is None:
                obj.id = 30
            self.added.append(obj)
        def flush(self):
            self.flushed += 1
        def commit(self):
            self.commits += 1
        def rollback(self):
            self.rollbacks += 1

    sess = Sess()
    bg = Bg()
    resp = type("Resp", (), {"status_code": 200})()

    out = asyncio.run(routes.create_research(
        request=routes.CreateResearchRequest(content="topic content for new session", session_id=None, locale="en"),
        response=resp,
        x_page_id="x",
        background_tasks=bg,
        current_user={"user_id": 1, "email": "e"},
        db=sess,
    ))

    assert out["code"] == 200
    assert any(c[0] is routes._background_process_prompt_and_update for c in bg.calls)
    # Ensure the call args include message_id (20) and session_db_id (10)
    fn, args = bg.calls[0]
    assert args[0] == 20 and args[1] == 10
    assert sess.commits == 1 and sess.flushed >= 1


def test_update_session_name_rollback_on_commit_error(monkeypatch):
    # session exists but commit fails -> rollback and 500
    class S: pass
    session_obj = S()
    class Sess(DummySession):
        def __init__(self):
            super().__init__(session=session_obj)
            self.rollback_called = 0
        def commit(self):
            raise RuntimeError("boom")
        def rollback(self):
            self.rollback_called += 1
    sess = Sess()
    out = asyncio.run(routes.update_session_name("sid", request=routes.UpdateSessionNameRequest(session_name="x"), current_user={"user_id": 1}, db=sess))
    assert out["code"] == ErrorCode.INTERNAL_SERVER_ERROR.value
    assert sess.rollback_called == 1


def test_delete_session_rollback_on_commit_error(monkeypatch):
    # session exists but commit fails -> rollback and 500
    class Obj: pass
    obj = Obj()
    class Sess(DummySession):
        def __init__(self):
            super().__init__(session=obj)
            self.rollback_called = 0
            self.deleted = []
        def delete(self, o):
            self.deleted.append(o)
        def commit(self):
            raise RuntimeError("boom")
        def rollback(self):
            self.rollback_called += 1
    sess = Sess()
    out = asyncio.run(routes.delete_session("sid", current_user={"user_id": 1}, db=sess))
    assert out["code"] == ErrorCode.INTERNAL_SERVER_ERROR.value
    assert obj in sess.deleted
    assert sess.rollback_called == 1
