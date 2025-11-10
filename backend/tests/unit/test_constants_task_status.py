import pytest

from app.constants.task_status import CreationStatus


def test_creation_status_constants():
    assert CreationStatus.PENDING == 'pending'
    assert CreationStatus.CREATING == 'creating'
    assert CreationStatus.CREATED == 'created'
    assert CreationStatus.FAILED == 'failed'


def test_creation_status_sets_and_helpers():
    assert set(CreationStatus.IN_PROGRESS) == {'pending', 'creating'}
    assert set(CreationStatus.FINISHED) == {'created', 'failed'}

    for s in ['pending', 'creating']:
        assert CreationStatus.is_in_progress(s) is True
        assert CreationStatus.is_finished(s) is False

    for s in ['created', 'failed']:
        assert CreationStatus.is_in_progress(s) is False
        assert CreationStatus.is_finished(s) is True

    # Unknown values should be False for both helpers
    for s in ['', 'unknown', None]:
        if s is None:
            continue
        assert CreationStatus.is_in_progress(s) is False
        assert CreationStatus.is_finished(s) is False
