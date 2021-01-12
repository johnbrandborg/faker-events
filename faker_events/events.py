"""
Events module for creating custom types and generating Messages
"""

from datetime import datetime, timedelta
import json
import random
import time
import types
import sys

from faker import Faker
from .handlers import Stream

__all__ = ['EventType', 'EventGenerator']


class EventType():
    """
    Base Class for new Event Types

    Parameters
    ----------
        limit: int
            The number of times to process the event

    Attributes
    ----------
        event: dict
            The base structure used for the Event
    """

    _next_event = None
    event = {}
    event_id = 1
    event_time = None

    def __init__(self, limit: int = None):
        self.limit = limit

    def __call__(self, profile=None):
        try:
            self.profiled(profile)
        except NotImplementedError:
            pass
        return self.event

    def __repr__(self):
        return f'{self.__class__.__name__}(limit={self.limit})'

    @property
    def next(self):
        """
        View the next event, or use a statement to set the event.
        """
        return self._next_event

    @next.setter
    def next(self, event):
        if isinstance(event, EventType):
            self._next_event = event
        else:
            raise TypeError("Event must be an EventType")

    def profiled(self, profile: dict) -> None:
        """
        If implemented the Event Creator will execute this method, and update
        the event dict on the instance before it is used.

        The profile can be used for adding details to the event, or updated
        to carry information onward to other events in the sequence.
        """
        raise NotImplementedError


class ExampleEvent(EventType):
    """
    Example Event if no event is supplied to the Generator
    """
    event = {
        'type': 'example',
    }

    def profiled(self, profile: dict) -> dict:
        updates = {
            'event_id': self.event_id,
            'user_id': profile.id,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
        }
        self.event.update(updates)


class EventGenerator():
    """
    The Event Generator is the central engine.  It creates profiles,
    and events to be sent to the Handlers.

    Parameters
    ----------
        num_profiles: int
            The number of times to process the event
        stream: faker_events.Stream
            Stream handler to use for sending messages
        use_profile_file: bool
            Creates and Uses a file for persistant profiles
        fake: Faker
            Customised Faker instance otherise one is created
    """

    _dtstamp = None
    _first_event = ExampleEvent()
    _state = []

    def __init__(self,
                 num_profiles: int = 10,
                 stream: Stream = None,
                 use_profile_file: bool = False,
                 fake: Faker = None):
        self.fake = fake
        self.num_profiles = num_profiles
        self.stream = stream if stream else Stream()

        if use_profile_file:
            try:
                with open('profiles.json') as profiles_file:
                    profiles_dicts = json.loads(profiles_file.read())
                    self.profiles = [types.SimpleNamespace(**profiles)
                                     for profiles in profiles_dicts]
            except FileNotFoundError:
                self.create_profiles()

                with open('profiles.json', 'w') as profiles_file:
                    profiles_dicts = [vars(item) for item in self.profiles]
                    profiles_file.write(json.dumps(profiles_dicts))
        else:
            self.create_profiles()

    def create_events(self):
        """
        Selects a profile to be used, and will request the Event Type
        to process the data if available.
        """

        count = 0

        while self._state:
            sindex = random.randint(0, len(self._state)-1)

            pindex = self._state[sindex][0]
            event = self._state[sindex][2]
            selected_profile = self.profiles[pindex]

            event.event_time = self._dtstamp.isoformat() \
                if self._dtstamp else datetime.now().isoformat()

            count += 1
            yield event(selected_profile)
            event.event_id += 1

            try:
                self._state[sindex][1] -= 1
            except TypeError:
                continue

            if self._state[sindex][1] == 0 and event.next is None:
                del self._state[sindex]
            elif self._state[sindex][1] == 0:
                self._state[sindex][1] = event.next.limit
                self._state[sindex][2] = event.next

        print(f'Event limit reached.  {count} in total generated')

    def create_profiles(self):
        """
        Creates the fake profiles that will be used for event creation.
        """
        fake = self.fake if self.fake else Faker()
        result = []

        for _ in range(self.num_profiles):
            gender = random.choice(['M', 'F'])

            if gender == 'F':
                first_name = fake.first_name_female()
                middle_name = fake.first_name_female()
                prefix_name = fake.prefix_female()
                suffix_name = fake.suffix_female()
            else:
                first_name = fake.first_name_male()
                middle_name = fake.first_name_male()
                prefix_name = fake.prefix_male()
                suffix_name = fake.suffix_male()

            last_name = fake.last_name()
            address = '{{building_number}}|{{street_name}}|{{state_abbr}}' \
                      '|{{postcode}}|{{city}}'
            address1 = fake.parse(address).split('|')
            profile = {
                'id': fake.unique.random_number(),
                'uuid': fake.uuid4(),
                'username': fake.user_name(),
                'gender': gender,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'prefix_name': prefix_name,
                'suffix_name': suffix_name,
                'birthdate': fake.date_of_birth(minimum_age=18,
                                                maximum_age=80).isoformat(),
                'blood_group': (random.choice(["A", "B", "AB", "O"]) +
                                random.choice(["+", "-"])),
                'email': f'{first_name}.{last_name}@{fake.domain_name()}',
                'employer': fake.company(),
                'job': fake.job(),
                'full_address1': ' '.join(address1),
                'building_number1': address1[0],
                'street_name1': address1[1].split(' ')[0],
                'street_suffix1': address1[1].split(' ')[1],
                'state1': address1[2],
                'postcode1': address1[3],
                'city1': address1[4],
                'phone1': fake.phone_number(),
                'full_address2': ' '.join(address1),
                'building_number2': address1[0],
                'street_name2': address1[1].split(' ')[0],
                'street_suffix2': address1[1].split(' ')[1],
                'state2': address1[2],
                'postcode2': address1[3],
                'city2': address1[4],
                'phone2': fake.phone_number(),
                'driver_license': fake.bothify('?#####'),
                'license_plate': fake.license_plate(),
            }

            result.append(types.SimpleNamespace(**profile))

        self.profiles = result

    @property
    def first_event(self):
        """
        View the first event, or use a statement to set the event.
        """
        return self._first_event

    @first_event.setter
    def first_event(self, event: EventType):
        if isinstance(event, EventType):
            self._first_event = event
        else:
            raise TypeError("Events must be an EventType instance")

        self.create_state()

    def live_stream(self, epm: int = 60, indent: int = None) -> str:
        """
        Produces a live stream of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """

        self._dtstamp = None

        if not self._state:
            self.create_state()

        try:
            for event in self.create_events():
                self.stream.send(json.dumps(event, indent=indent))
                time.sleep(random.random() * 60/epm)
        except KeyboardInterrupt:
            print('\nStopping Event Stream', file=sys.stderr)

    def batch(self,
              start: datetime,
              finish: datetime,
              epm: int = 60,
              indent: int = None) -> str:
        """
        Produces a batch of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """

        self._dtstamp = start

        if not self._state:
            self.create_state()

        try:
            for event in self.create_events():
                self.stream.send(json.dumps(event, indent=indent))
                self._dtstamp += timedelta(seconds=random.random() * 60/epm)

                if self._dtstamp >= finish:
                    print('Finish time reached', file=sys.stderr)
                    break

        except KeyboardInterrupt:
            print('\nStopping Event Batch', file=sys.stderr)

    def create_state(self):
        """
        Creates the state table used for tracking event generation
        """
        self._state = [[index, self.first_event.limit, self.first_event]
                       for index, _ in enumerate(self.profiles)]
