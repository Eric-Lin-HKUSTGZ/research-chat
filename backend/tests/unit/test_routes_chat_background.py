import types

import pytest

from app.routes import chat_routes as routes
from app.constants.task_status import CreationStatus


class DummyLLM:
    def __init__(self, *a, **k):
        self.calls = []
        # sequence of responses for 5 calls
        self._seq = [
            "kw1, kw2",  # keywords
            "inspiration text",  # inspiration
            "preliminary plan",  # plan
            "criticisms",  # criticism
            "final plan",  # final
        ]
    def get_response(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        return self._seq[min(len(self.calls)-1, len(self._seq)-1)]


class DummyProc:
    def __init__(self, message_id=1):
        self.id = 5
        self.message_id = message_id
        self.user_id = 1
        self.email = "e"
        self.process_info = {"logs": []}
        self.creation_status = CreationStatus.CREATING
        self.created_at = None
        self.updated_at = None


class DummyMsg:
    def __init__(self, id=1):
        self.id = id
        self.result_papers = None
        self.updated_at = None
        self.extra_info = None


class DummySession:
    def __init__(self, proc, msg):
        self.proc = proc
        self.msg = msg
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
    def execute(self, stmt):
        # not used in background success path
        return types.SimpleNamespace(first=lambda: None)
    def scalar(self, stmt):
        # our monkeypatched select attaches a marker attribute
        marker = getattr(stmt, 'marker', None)
        if marker == 'process':
            return self.proc
        if marker == 'message':
            return self.msg
        return None
    def commit(self):
        self.commits += 1
    def rollback(self):
        self.rollbacks += 1
    def close(self):
        self.closed = True


def test_background_process_prompt_and_update_success(monkeypatch, tmp_path):
    # Monkeypatch SessionLocal used inside background function
    proc = DummyProc(message_id=1)
    msg = DummyMsg(id=1)
    sess = DummySession(proc, msg)
    monkeypatch.setattr(routes, 'SessionLocal', lambda: sess)

    # Monkeypatch select to tag targets for our DummySession.scalar
    def fake_select(target):
        class _S:
            def __init__(self, target):
                self.marker = 'message' if target is routes.ResearchChatMessage else (
                    'process' if target is routes.ResearchChatProcessInfo else 'other'
                )
            def where(self, *a, **k):
                return self
        return _S(target)
    monkeypatch.setattr(routes, 'select', fake_select)

    # Monkeypatch LLM and HTTP helpers
    monkeypatch.setattr(routes, 'LLMClient', DummyLLM)
    monkeypatch.setattr(routes, 'get_newest_paper', lambda q: [{"title": "t1", "abstract": "a1"}])
    monkeypatch.setattr(routes, 'get_highly_cited_paper', lambda q: [{"title": "t2", "abstract": "a2"}])
    monkeypatch.setattr(routes, 'get_relevence_paper', lambda q: [{"title": "t3", "abstract": "a3"}])

    # Run background processing (synchronous)
    routes._background_process_prompt_and_update(
        message_id=1,
        session_db_id=1,
        user_id=1,
        user_email='e',
        content='topic',
        locale='en'
    )

    # Assertions: process moved to CREATED and message has result data
    assert proc.creation_status == CreationStatus.CREATED
    assert isinstance(msg.result_papers, dict)
    assert 'response' in msg.result_papers
    assert sess.commits >= 1
