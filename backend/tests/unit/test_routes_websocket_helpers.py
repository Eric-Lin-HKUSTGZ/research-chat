import asyncio
import types

import pytest

from app.routes import websocket_routes as ws


class DummyWS:
    def __init__(self, query=None):
        self.query_params = query or {}
        self._closed = False
        self.close_args = None
        self.sent = []
        class State:
            def __init__(self):
                self.name = 'CONNECTED'
        self.client_state = State()
    async def accept(self):
        return None
    async def close(self, code=1000, reason=None):
        self._closed = True
        self.close_args = (code, reason)
        self.client_state.name = 'DISCONNECTED'
    async def send_json(self, data):
        self.sent.append(data)


def test_authenticate_websocket_missing_token():
    req = DummyWS()
    out = asyncio.run(ws.authenticate_websocket(req))
    assert out is None


def test_authenticate_websocket_valid(monkeypatch):
    # monkeypatch jwt_manager.decode_token
    monkeypatch.setattr(ws.jwt_manager, 'decode_token', lambda t: {"user_id": 1, "email": "e"})
    req = DummyWS(query={"token": "t", "locale": "en"})
    out = asyncio.run(ws.authenticate_websocket(req))
    assert out == {"user_id": 1, "email": "e", "locale": "en"}


def test_validate_message_exists(monkeypatch):
    # Patch SessionLocal to return an object with execute().scalar_one_or_none()
    class DummySession:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def execute(self, stmt):
            class Res:
                def scalar_one_or_none(self):
                    return types.SimpleNamespace(message_id=1)
            return Res()
    monkeypatch.setattr(ws, 'SessionLocal', lambda: DummySession())
    out = asyncio.run(ws.validate_message_exists(1))
    assert getattr(out, 'message_id', None) == 1


def test_websocket_status_rejects_on_missing_auth(monkeypatch):
    # user_info None -> should close with 1003
    dummy = DummyWS(query={})
    out = asyncio.run(ws.websocket_status(dummy, message_id=1, user_info=None, task=None))
    assert dummy._closed is True
    assert dummy.close_args[0] == 1003
    assert 'Authentication failed' in (dummy.close_args[1] or '')


def test_websocket_status_rejects_on_missing_task(monkeypatch):
    # task None -> should close with 1003 and specific reason
    dummy = DummyWS(query={})
    out = asyncio.run(ws.websocket_status(dummy, message_id=1, user_info={"user_id": 1, "email": "e"}, task=None))
    assert dummy._closed is True
    assert dummy.close_args[0] == 1003
    assert 'Task not found' in (dummy.close_args[1] or '')


def test_websocket_status_loop_sends_on_change_and_breaks_on_finished(monkeypatch):
    # Prepare a sequence: creating (send), creating same (no send), created (send + break)
    seq = [
        types.SimpleNamespace(message_id=1, creation_status=ws.CreationStatus.CREATING, process_info={"logs": ["l1"]}),
        types.SimpleNamespace(message_id=1, creation_status=ws.CreationStatus.CREATING, process_info={"logs": ["l1"]}),
        types.SimpleNamespace(message_id=1, creation_status=ws.CreationStatus.CREATED, process_info={"logs": ["done"]}),
    ]

    class SeqFactory:
        def __init__(self, sequence):
            self.sequence = sequence
            self.i = 0
        def __call__(self):
            factory = self
            class DummySession:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc, tb):
                    return False
                def execute(self, stmt):
                    class Res:
                        def scalar_one_or_none(self_inner):
                            if factory.i >= len(factory.sequence):
                                return factory.sequence[-1]
                            val = factory.sequence[factory.i]
                            factory.i += 1
                            return val
                    return Res()
            return DummySession()

    monkeypatch.setattr(ws, 'SessionLocal', SeqFactory(seq))
    # No delay between polling iterations
    monkeypatch.setattr(ws.Config, 'WS_POLL_INTERVAL_SECONDS', 0)

    dummy = DummyWS(query={})
    out = asyncio.run(ws.websocket_status(dummy, message_id=1, user_info={"user_id": 1, "email": "e"}, task=object()))

    # Should have sent exactly 2 messages: first creating, then created
    assert len(dummy.sent) == 2
    assert dummy.sent[0]['data']['status'] == ws.CreationStatus.CREATING
    assert dummy.sent[1]['data']['status'] == ws.CreationStatus.CREATED
    assert dummy._closed is True


def test_websocket_status_db_exception_breaks_without_send(monkeypatch):
    class BoomSession:
        def __enter__(self):
            raise RuntimeError('db boom')
        def __exit__(self, exc_type, exc, tb):
            return False
    monkeypatch.setattr(ws, 'SessionLocal', lambda: BoomSession())

    dummy = DummyWS(query={})
    out = asyncio.run(ws.websocket_status(dummy, message_id=1, user_info={"user_id": 1, "email": "e"}, task=object()))

    # No messages sent due to DB exception; connection eventually closed cleanly
    assert dummy.sent == []
    assert dummy._closed is True
    assert dummy.close_args[0] == 1000


def test_websocket_status_exception_triggers_error_message(monkeypatch):
    # First send_json raises -> outer except -> error message sent
    seq = [types.SimpleNamespace(message_id=1, creation_status=ws.CreationStatus.CREATING, process_info={"logs": []})]

    class SeqFactory:
        def __init__(self, sequence):
            self.sequence = sequence
            self.i = 0
        def __call__(self):
            factory = self
            class DummySession:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc, tb):
                    return False
                def execute(self, stmt):
                    class Res:
                        def scalar_one_or_none(self_inner):
                            return factory.sequence[min(factory.i, len(factory.sequence)-1)]
                    return Res()
            return DummySession()

    class FlakyWS(DummyWS):
        def __init__(self, query=None):
            super().__init__(query=query)
            self._first = True
        async def send_json(self, data):
            if self._first:
                self._first = False
                raise RuntimeError('send fail')
            self.sent.append(data)

    monkeypatch.setattr(ws, 'SessionLocal', SeqFactory(seq))
    dummy = FlakyWS(query={})

    out = asyncio.run(ws.websocket_status(dummy, message_id=1, user_info={"user_id": 1, "email": "e"}, task=object()))

    # Error handler should have attempted to send a 500 message
    assert any(item.get('code') == 500 for item in dummy.sent)
    assert dummy._closed is True


def test_websocket_status_close_timeout_path(monkeypatch):
    # Make close() exceed the 0.2s wait_for timeout
    class SlowCloseWS(DummyWS):
        def __init__(self, query=None):
            super().__init__(query=query)
            self.close_started = False
        async def close(self, code=1000, reason=None):
            self.close_started = True
            # Sleep slightly longer than the 0.2s timeout
            await asyncio.sleep(0.25)
            # If ever awaited to completion (not in this test), mark closed
            self._closed = True
            self.close_args = (code, reason)
            self.client_state.name = 'DISCONNECTED'

    # Return created immediately so loop breaks quickly
    class OneShotSession:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def execute(self, stmt):
            class Res:
                def scalar_one_or_none(self):
                    return types.SimpleNamespace(message_id=1, creation_status=ws.CreationStatus.CREATED, process_info={"logs": []})
            return Res()

    monkeypatch.setattr(ws, 'SessionLocal', lambda: OneShotSession())
    dummy = SlowCloseWS(query={})

    # Should not raise despite close timing out; connection won't be marked closed by our dummy
    out = asyncio.run(ws.websocket_status(dummy, message_id=1, user_info={"user_id": 1, "email": "e"}, task=object()))
    assert dummy.close_started is True
    # Since close timed out, our dummy did not flip to DISCONNECTED/closed
    assert dummy._closed is False
