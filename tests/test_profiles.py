""" Profiles Tests
"""

import json
from types import SimpleNamespace
from unittest.mock import mock_open, patch

from faker import Faker
import pytest
from faker_events import ProfileGenerator

PROFILE_SAMPLE = {
    'id': '1',
    'first_name': 'John',
    'last_name': 'Smith',
}


@pytest.fixture
def profile_sample():
    """ Returns a Profile to be used on Events
    """
    return SimpleNamespace(**PROFILE_SAMPLE)


@pytest.fixture
def profile_json():
    """ Returns a list with a Profile to be use in Files
    """
    return json.dumps([PROFILE_SAMPLE])


def test_generator_profile_creation():
    """
    Load should create entries using SimpleNamespace, and a predefined set
    of attributes, to be used in the profiler functions.
    """
    profiles_generator = ProfileGenerator()
    profiles_generator.load(num_profiles=1)

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

    assert len(profiles_generator.entries) == 1
    assert isinstance(profiles_generator.entries[0], SimpleNamespace)

    for attr in attributes:
        assert hasattr(profiles_generator.entries[0], attr)


def test_generator_profile_file_read(profile_json, profile_sample):
    """ Use a file for profile data if found
    """
    mocked_file = mock_open(read_data=profile_json)
    with patch('faker_events.profiles.open', mocked_file) as mopen:
        profiles_generator = ProfileGenerator()
        profiles_generator.load(num_profiles=1, profiles_file='test')

    mopen.assert_called_once_with('test', encoding='utf-8')
    assert profiles_generator.entries == [profile_sample]


def test_generator_profile_file_create():
    """ Create a file for the profile data if not found
    """
    mopen = mock_open()
    mopen.side_effect = [FileNotFoundError, mopen.return_value]

    with patch('builtins.open', mopen):
        profiles_generator = ProfileGenerator()
        profiles_generator.load(num_profiles=1, profiles_file='test.json')

        mopen.assert_called_with('test.json', 'w', encoding='utf-8')


def test_generator_can_accept_faker_instance():
    """ Use a Faker Instance if supplied to the Generator
    """
    profiles_generator = ProfileGenerator()
    assert profiles_generator.fake.locales == ['en_US']

    profiles_generator = ProfileGenerator(fake=Faker(locale=['en_AU']))
    assert profiles_generator.fake.locales == ['en_AU']
