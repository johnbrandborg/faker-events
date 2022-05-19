""" Events Tests
"""

from datetime import datetime, timedelta
import json
from types import GeneratorType, SimpleNamespace
from unittest.mock import Mock

import pytest

from faker_events.events import Event, EventGenerator

EVENT_SAMPLE = {
    'event_time': '',
    'type': 'test',
    'event_id': '',
    'user_id': '',
    'first_name': '',
    'last_name': '',
}


class CaptureStream():
    """ Stream used for testing
    """
    captured = []

    def send(self, message):
        self.captured.append(message)


@pytest.fixture
def event():
    """ Returns an Event with no profiled method
    """
    event = {'test': True}
    return Event(event)


@pytest.fixture
def event_profiled():
    """ Returns an Event with a profiled method
    """
    event = {'Profiled': False}

    def profiler(self, profile):
        return {'Profiled': True}

    return Event(event, profiler)


@pytest.fixture
def event_generator(profile_sample):

    class MockProfilerGenerator:
        entries = profile_sample

    capture = CaptureStream()
    event_generator = EventGenerator(MockProfilerGenerator())
    event_generator.set_stream(capture)
    event_generator.set_first_events = Event(EVENT_SAMPLE)
    return event_generator


@pytest.fixture
def profile_sample():
    """ Returns a Profile to be used on Events
    """
    return [SimpleNamespace(id='1', first_name='John', last_name='Smith')]


def test_event_returns_unprofiled(event):
    """ Event call only returns the event data
    """
    assert event.process(0, [], "") == ({'test': True}, True)


def test_event_returns_profiles(event_profiled):
    """ Event call returns the profiled data
    """
    result, _ = event_profiled.process(0, [{}], "")
    assert result.get("Profiled")


def test_event_repr(event):
    """ Event Repr format check
    """
    assert repr(event) == "Event({'test': True}, None, limit=1)"


def test_event_next_get(event):
    """ Next method returns None if not set
    """
    assert event.next is None


def test_event_next_set(event):
    """ Next method returns Event if set
    """
    next_event = Event({})
    event >> next_event

    assert event.next == [next_event]


def test_event_next_set_type_check(event):
    """ Method requires Event Type
    """
    with pytest.raises(TypeError):
        event.next = 'not an event'


def test_example_event_update(profile_sample):
    """ ExampleEvent Output
    """
    event_time = datetime.now().isoformat("Z")

    def profiler(event, profile):
        return {
            'event_time': event.time,
            'event_id': event.id,
            'user_id': profile.id,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
        }
    example = Event(EVENT_SAMPLE, profiler)
    example.process(0, profile_sample, event_time)

    assert example.data == {
        'type': 'test',
        'event_time': event_time,
        'event_id': 1,
        'user_id': '1',
        'first_name': 'John',
        'last_name': 'Smith'
    }


def test_generator_create_events(event_generator):
    """ Create Event returns a Generator that produces a dictionary
    """
    event_generator._dtstamp = datetime(2019, 1, 1)

    expected = {
        'event_id': 1,
        'event_time': '2019-01-01T00:00:00',
        'first_name': 'John',
        'last_name': 'Smith',
        'type': 'example',
        'user_id': '1'
    }
    event_gen = event_generator.create_events()

    assert isinstance(event_gen, GeneratorType)
    assert list(event_gen) == [expected]


def test_generator_create_events_resets_state(event_generator):
    """ When a state table is empty create_events should reset it
    """
    event_generator._state_table = []

    m_reset_state_table = Mock()
    event_generator._reset_state_table = m_reset_state_table
    list(event_generator.create_events())

    m_reset_state_table.assert_called_once()


def test_generator_first_events_set(event_generator):
    """ First event method sets the Event to be used initially
        Setting the events also resets the state table
    """
    m_reset_state_table = Mock()
    event_generator._reset_state_table = m_reset_state_table
    event_generator.set_first_events = Event({})

    assert isinstance(event_generator._events[0], Event)
    m_reset_state_table.assert_called_once()


def test_generator_first_events_get_type_check(event_generator):
    """ First event method checks that the type is Event
    """
    with pytest.raises(TypeError):
        event_generator.set_first_events = 'not an Event Type'


def test_generator_live_stream(event_generator):
    """ Live stream rns randomly timed event generation from now
    """
    event_generator._stream.captured = []
    event_generator.start()

    dtstamp = datetime.now().isoformat()
    expected_message = {
        'type': 'example',
        'event_time': dtstamp.split('T')[0],
        'event_id': 1,
        'user_id': '1',
        'first_name': 'John',
        'last_name': 'Smith'
    }

    assert len(event_generator._stream.captured) == 1
    sent_message = json.loads(event_generator._stream.captured[0])
    sent_message['event_time'] = sent_message['event_time'].split('T')[0]
    assert sent_message == expected_message


def test_generator_batch_stream(event_generator):
    """ Batch stream randomly timed event generation from now
    """
    start = datetime(2019, 1, 1)
    finish = start + timedelta(minutes=1)
    event_generator.stream.captured = []
    event_generator.batch(start, finish)

    dtstamp = event_generator._dtstamp
    expected_message = {
        'type': "example",
        'event_time': dtstamp.isoformat().split('T')[0],
        'event_id': 1,
        'user_id': '1',
        "first_name": "John",
        "last_name": "Smith"
    }

    assert len(event_generator.stream.captured) == 1
    sent_message = json.loads(event_generator.stream.captured[0])
    sent_message['event_time'] = sent_message['event_time'].split('T')[0]
    assert sent_message == expected_message


def test_generator_batch_completes(event_generator):
    """ Stop when finish time is past
    """
    start = datetime(2019, 1, 1)
    finish = start - timedelta(minutes=1)
    event_generator.batch(start, finish)

    assert len(event_generator.stream.captured) == 0


def test_generator_changes_next_event(event_generator):
    """ When the limit exceeds the state entry updates the event
    """
    eventa = Event({'name': 'a'}, limit=1)
    eventb = Event({'name': 'b'}, limit=1)
    event_generator.first_events = eventa
    eventa >> eventb
    expect_events = [{'name': 'a'}, {'name': 'b'}]

    assert list(event_generator.create_events()) == expect_events
