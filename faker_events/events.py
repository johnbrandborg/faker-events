"""
Events module for creating custom types and generating Messages
"""

from datetime import datetime, timedelta
import json
import random
import time
import types
import sys

import faker
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
    event_id = 0
    event_time = None

    def __init__(self, limit: int = None):
        self.limit = limit

    def __call__(self, profile=None) -> dict:
        try:
            self.profiled(profile)
        except NotImplementedError:
            pass
        return self.event

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(limit={self.limit})'

    @property
    def next(self):
        """
        View the next event, or use a statement to set the event.
        """
        return self._next_event

    @next.setter
    def next(self, event) -> None:
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
            'event_time': self.event_time,
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
    _state_table = []
    profiles = []

    def __init__(self,
                 num_profiles: int = 10,
                 stream: Stream = None,
                 use_profile_file: bool = False,
                 fake: faker.Faker = None):
        self.num_profiles = num_profiles
        self.stream = stream if stream else Stream()

        self.fake = fake if fake and \
            isinstance(fake, faker.Faker) else faker.Faker()

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

    def create_events(self) -> dict:
        """
        Selects a profile to be used, and will request the Event Type
        to process the data if available.
        """

        total_count = 0

        if not self._state_table:
            self._reset_state_table()

        while self._state_table:
            sindex = random.randint(0, len(self._state_table)-1)
            pindex = self._state_table[sindex][0]
            event = self._state_table[sindex][2]
            selected_profile = self.profiles[pindex]

            event.event_time = self._dtstamp.isoformat('T') \
                if self._dtstamp else datetime.now().isoformat('T')

            total_count += 1
            event.event_id += 1
            yield event(selected_profile)

            if isinstance(self._state_table[sindex][1], int):
                self._state_table[sindex][1] -= 1
                self._process_state_entry(sindex, event)

        print(f'Event limit reached.  {total_count} in total generated')

    def create_profiles(self) -> None:
        """
        Creates the fake profiles that will be used for event creation.
        """
        result = []

        for _ in range(self.num_profiles):
            gender = random.choice(['M', 'F'])

            if gender == 'F':
                first_name = self.fake.first_name_female()
                middle_name = self.fake.first_name_female()
                prefix_name = self.fake.prefix_female()
                suffix_name = self.fake.suffix_female()
            else:
                first_name = self.fake.first_name_male()
                middle_name = self.fake.first_name_male()
                prefix_name = self.fake.prefix_male()
                suffix_name = self.fake.suffix_male()

            last_name = self.fake.last_name()
            address = '{{building_number}}|{{street_name}}|{{state_abbr}}' \
                      '|{{postcode}}|{{city}}'
            address1 = self.fake.parse(address).split('|')
            profile = {
                'id': self.fake.unique.random_number(),
                'uuid': self.fake.uuid4(),
                'username': self.fake.user_name(),
                'gender': gender,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'prefix_name': prefix_name,
                'suffix_name': suffix_name,
                'birthdate': self.fake.date_of_birth(minimum_age=18,
                                                     maximum_age=80)
                            .isoformat(),
                'blood_group': (random.choice(["A", "B", "AB", "O"]) +
                                random.choice(["+", "-"])),
                'email': f'{first_name}.{last_name}@{self.fake.domain_name()}',
                'employer': self.fake.company(),
                'job': self.fake.job(),
                'full_address1': ' '.join(address1),
                'building_number1': address1[0],
                'street_name1': address1[1].split(' ')[0],
                'street_suffix1': address1[1].split(' ')[1],
                'state1': address1[2],
                'postcode1': address1[3],
                'city1': address1[4],
                'phone1': self.fake.phone_number(),
                'full_address2': ' '.join(address1),
                'building_number2': address1[0],
                'street_name2': address1[1].split(' ')[0],
                'street_suffix2': address1[1].split(' ')[1],
                'state2': address1[2],
                'postcode2': address1[3],
                'city2': address1[4],
                'phone2': self.fake.phone_number(),
                'driver_license': self.fake.bothify('?#####'),
                'license_plate': self.fake.license_plate(),
            }

            result.append(types.SimpleNamespace(**profile))
        self.profiles = result

    @property
    def first_event(self) -> EventType:
        """
        View the first event, or use a statement to set the event.
        """
        return self._first_event

    @first_event.setter
    def first_event(self, event: EventType) -> None:
        if isinstance(event, EventType):
            self._first_event = event
        else:
            raise TypeError("Events must be an EventType instance")

        self._reset_state_table()

    def live_stream(self, epm: int = 60, indent: int = None) -> None:
        """
        Produces a live stream of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """

        self._dtstamp = None

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
              indent: int = None) -> None:
        """
        Produces a batch of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """

        self._dtstamp = start

        try:
            for event in self.create_events():
                if self._dtstamp >= finish:
                    print('Finish time reached', file=sys.stderr)
                    break
                self.stream.send(json.dumps(event, indent=indent))
                self._dtstamp += timedelta(seconds=random.random() * 60/epm)
        except KeyboardInterrupt:
            print('\nStopping Event Batch', file=sys.stderr)

    def _reset_state_table(self) -> None:
        self._state_table = [[index, self.first_event.limit, self.first_event]
                             for index, _ in enumerate(self.profiles)]

    def _process_state_entry(self, index: int, event: EventType) -> None:
        if self._state_table[index][1] == 0 and event.next is None:
            del self._state_table[index]
        elif self._state_table[index][1] == 0:
            self._state_table[index][1] = event.next.limit
            self._state_table[index][2] = event.next
