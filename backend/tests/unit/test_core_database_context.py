import pytest

from app.core import database as dbmod


class DummySession:
    def __init__(self):
        self.commit_called = False
        self.rollback_called = False
        self.closed = False

    # support context manager style used in get_db_context
    def close(self):
        self.closed = True

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True


def test_get_db_context_commit(monkeypatch):
    monkeypatch.setattr(dbmod, "SessionLocal", lambda: DummySession())
    with dbmod.get_db_context() as s:
        # do nothing, should commit on exit
        assert isinstance(s, DummySession)
    # After exiting, the DummySession instance used inside context is not directly accessible
    # So we create another and assert attributes type. Instead, patch to capture instance.


def test_get_db_context_commit_and_rollback(monkeypatch):
    captured = {}

    def factory():
        sess = DummySession()
        captured["sess"] = sess
        return sess

    monkeypatch.setattr(dbmod, "SessionLocal", factory)

    # Success path commits
    with dbmod.get_db_context():
        pass
    assert captured["sess"].commit_called is True
    assert captured["sess"].rollback_called is False
    assert captured["sess"].closed is True

    # Exception path rolls back and re-raises
    captured.clear()
    monkeypatch.setattr(dbmod, "SessionLocal", factory)
    with pytest.raises(RuntimeError):
        with dbmod.get_db_context():
            raise RuntimeError("boom")
    assert captured["sess"].commit_called is False
    assert captured["sess"].rollback_called is True
    assert captured["sess"].closed is True
