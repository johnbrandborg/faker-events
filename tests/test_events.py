""" Events Tests
"""

from datetime import datetime
import json
from types import GeneratorType, SimpleNamespace
from unittest.mock import Mock, mock_open, patch

import faker
import pytest

from faker_events.events import (
    EventGenerator,
    EventType,
    ExampleEvent
)


PROFILE_SAMPLE = {
    'id': 1,
    'user_id': 1,
    'first_name': 'John',
    'last_name': 'Smith',
}


@pytest.fixture
def event():
    """ Returns an Event with no profiled method
    """
    return EventType()


@pytest.fixture
def event_profiled():
    """ Returns an Event with a profiled method
    """
    class Event(EventType):
        """ SubClass
        """
        def profiled(self, _):
            """ Implement Method
            """
            self.event['Profiled'] = True
    return Event()


@pytest.fixture
def event_generator_class(monkeypatch, profile_sn):
    mcreate_profiles = Mock()
    monkeypatch.setattr(EventGenerator, 'create_profiles', mcreate_profiles)
    monkeypatch.setattr(EventGenerator, 'profiles', [profile_sn])
    return EventGenerator


@pytest.fixture
def event_generator(event_generator_class):
    event_generator = event_generator_class()
    event_generator.first_event = ExampleEvent(1)
    return event_generator


@pytest.fixture
def profile_sn():
    """ Returns a Profile to be used on Events
    """
    return SimpleNamespace(**PROFILE_SAMPLE)


@pytest.fixture
def profile_json():
    """ Returns a list with a Profile to be use in Files
    """
    return json.dumps([PROFILE_SAMPLE])


def test_event_returns_unprofiled(event):
    """ Event Call only returns the event data
    """
    assert event() == {}


def test_event_returns_profiles(event_profiled):
    """ Event Call returns the profiled data
    """
    assert event_profiled()['Profiled']


def test_event_repr(event):
    """ Repr format check
    """
    assert repr(event) == 'EventType(limit=None)'


def test_event_next_get(event):
    """ Method returns None if not set
    """
    assert event.next is None


def test_event_next_set(event):
    """ Method returns Event if set
    """
    next_event = EventType()
    event.next = next_event

    assert event.next == next_event


def test_event_next_set_raises_typeerror(event):
    """ Method requires EventType
    """
    with pytest.raises(TypeError):
        event.next = 'String'


def test_event_profiled_notimplemented(event):
    """ Unprofiled Event raises NotImplementedError
    """
    with pytest.raises(NotImplementedError):
        event.profiled(None)


def test_example_event_update(profile_sn):
    """ ExampleEvent Output
    """
    example_event = ExampleEvent()
    example_event.profiled(profile_sn)

    assert example_event.event == {
        'type': 'example',
        'event_time': None,
        'event_id': 0,
        'user_id': 1,
        'first_name': 'John',
        'last_name': 'Smith'
    }


def test_generator_profile_file_read(profile_json, profile_sn):
    """ Use a file for profile data if found
    """
    mocked_file = mock_open(read_data=profile_json)
    with patch('faker_events.events.open', mocked_file) as mopen:
        event_generator = EventGenerator(1, None, True)

    mopen.assert_called_once_with('profiles.json')
    assert event_generator.profiles == [profile_sn]


def test_generator_profile_file_create(event_generator_class):
    """ Create a file for the profile data if not found
    """
    mopen = mock_open()
    mopen.side_effect = [FileNotFoundError, mopen.return_value]

    with patch('faker_events.events.open', mopen):
        event_generator_class(1, None, True)

    assert mopen.call_count == 2


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
        'user_id': 1
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


def test_generator_can_accept_faker_instance(event_generator_class):
    """ Use a Faker Instance if supplied to the Generator
    """
    event_generator = event_generator_class()
    assert event_generator.fake.locales == ['en_US']

    event_generator = event_generator_class(fake=faker.Faker(locale=['en_AU']))
    assert event_generator.fake.locales == ['en_AU']


def test_generator_profile_creation():
    """ Profiles are created when the Event Generator is created
    """
    event_gen = EventGenerator(1)

    attributes = [
        'id',
        'uuid',
        'username',
        'gender',
        'first_name',
        'last_name',
        'prefix_name',
        'suffix_name',
        'birthdate',
        'blood_group',
        'email',
        'employer',
        'job',
        'full_address1',
        'building_number1',
        'street_name1',
        'street_suffix1',
        'state1',
        'postcode1',
        'city1',
        'phone1',
        'full_address2',
        'building_number2',
        'street_name2',
        'street_suffix2',
        'state2',
        'postcode2',
        'city2',
        'phone2',
        'driver_license',
        'license_plate',
    ]

    assert len(event_gen.profiles) == 1
    assert isinstance(event_gen.profiles[0], SimpleNamespace)

    # TODO Broken by the Mocking of EventGenerator
    for attr in attributes:
        assert hasattr(event_gen.profiles[0], attr)
