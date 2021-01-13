import pytest

from faker_events.events import EventType


@pytest.fixture
def event():
    return EventType()


def test_event_is_callable(event):
    assert callable(event)


def test_EventType_profiled_NotImplemented():
    with pytest.raises(NotImplementedError):
        EventType.profiled(None, None)
