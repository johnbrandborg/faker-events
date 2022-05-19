""" Events Tests
"""

from datetime import datetime, timedelta
from types import GeneratorType, SimpleNamespace
from unittest.mock import Mock

import pytest

from faker_events.events import Event, EventGenerator, ProfilesGenerator


structure = {
    'type': 'test',
    'event_id': '',
    'user_id': '',
    'first_name': '',
    'last_name': '',
}


def profiler(event, profile):
    return {
        'event_id': event.id,
        'user_id': profile.id,
        'first_name': profile.first_name,
        'last_name': profile.last_name,
    }


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
def profile_sample():
    """ Returns a Profile to be used on Events
    """
    return [SimpleNamespace(id='1', first_name='John', last_name='Smith')]


# Event Testing

def test_event_returns_unprofiled(event):
    """ Event call only returns the event data, and delivery indicator
    """
    assert event.process(0, [], "") == ({'test': True}, True)


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
    example = Event(structure, profiler)
    example.process(0, profile_sample, event_time)

    assert example.data == {
        'type': 'test',
        'event_id': '1',
        'user_id': '1',
        'first_name': 'John',
        'last_name': 'Smith'
    }


# EventGenerator Testing

@pytest.fixture
def event_generator(profile_sample):
    """ Returns an Instance of the EventGenerator, but modified for testing
    """
    Event.clear()

    class CaptureStream():
        """ Stream used for testing
        """
        captured = []

        def send(self, message):
            self.captured.append(message)

    profiles_generator = ProfilesGenerator()
    profiles_generator.entries = profile_sample

    EventGenerator.set_stream(CaptureStream())
    EventGenerator.set_first_events(Event(structure, profiler))
    return EventGenerator(profiles_generator)


def test_generator_create_events_lazily(event_generator):
    """ Create profiled events on demand for memory effiency
    """
    assert isinstance(event_generator.create_events(), GeneratorType)


def test_generator_create_events_resets_state(event_generator):
    """ When a state table is empty create_events should reset it
    """
    event_generator._state_table = []

    m_reset_state_table = Mock()
    event_generator._reset_state_table = m_reset_state_table
    list(event_generator.create_events())

    m_reset_state_table.assert_called_once()


def test_generator_first_events_set_type_check(event_generator):
    """ Setting the first event method checks that the type is Event
    """
    with pytest.raises(TypeError):
        event_generator.set_first_events('not an Event Type')


def test_generator_live_stream(event_generator):
    """ Live stream sends randomly timed event generation from now
    """
    event_generator.start()

    expected_message = {
        'type': 'test',
        'event_id': '1',
        'user_id': '1',
        'first_name': 'John',
        'last_name': 'Smith'
    }

    assert len(event_generator._stream.captured) == 1
    sent_message = event_generator._stream.captured[0]
    assert sent_message == expected_message


def test_generator_batch_stream(event_generator):
    """ Batch stream sends randomly timed event generation from the start time
    """
    start = datetime(2019, 1, 1)
    finish = start + timedelta(minutes=1)
    event_generator.batch(start, finish)
    event_generator.start()

    expected_message = {
        'type': 'test',
        'event_id': '1',
        'user_id': '1',
        'first_name': 'John',
        'last_name': 'Smith'
    }

    assert len(event_generator._stream.captured) == 1
    sent_message = event_generator._stream.captured[0]
    assert sent_message == expected_message
