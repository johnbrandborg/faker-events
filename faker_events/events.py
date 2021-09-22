"""
Events module for creating custom types and generating Messages
"""

from datetime import datetime, timedelta
import json
from random import choice, randint, random
from sys import stderr
from time import sleep
from types import SimpleNamespace

from faker import Faker
from .handlers import Stream

__all__ = ['Event', 'EventGenerator']


example_event = {
    'event_time': '',
    'type': 'example',
    'event_id': '',
    'user_id': '',
    'first_name': '',
    'last_name': ''
}


def profile_example(self, profile: dict) -> dict:
    return {
        'event_time': self.event_time,
        'event_id': self.event_id,
        'user_id': profile.id,
        'first_name': profile.first_name,
        'last_name': profile.last_name
    }


class Event():
    """
    An Event Types that will produced a defined number of events. The event
    maybe static or dynamic by suppling a function to modify the event.

    Parameters
    ----------
        event: dict
            Base data structure used for events.  All values must be declared
            for the automatic value updates to occur.
        profiler: function
            A function that takes the profile dict and merges the values. The
            event can be updated within the function, or return the dict for
            the update to occur automatically.
        limit: int
            The number of times to process the event.
    """

    def __init__(self,
                 event: dict,
                 profiler: callable = None,
                 limit: int = None):
        self.event = event
        self.profiler = profiler
        self.limit = limit
        self.event_id = 0
        self.event_time = None
        self._next_event = None

    def __call__(self, profile=None) -> dict:
        if callable(self.profiler):
            returned = self.profiler(self, profile)
            if returned:
                self._update_values(self.event, returned)
        return self.event

    def __str__(self):
        return self()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.event}, {self.profiler}, limit={self.limit})'

    def __lshift__(self, other):
        other.next = self
        return self

    def __rshift__(self, other):
        self.next = other
        return other

    @property
    def next(self):
        """
        View the next event, or use a statement to set the event.
        """
        return self._next_event

    @next.setter
    def next(self, events) -> None:
        if isinstance(events, Event):
            self._next_event = [events]
        elif not isinstance(events, list):
            raise TypeError("An Event or list of Event Types is required")
        elif all((isinstance(event, Event) for event in events)):
            self._next_event = events
        else:
            raise TypeError("Events must be only Event Type instances")

    @staticmethod
    def _update_values(dict1: dict, dict2: dict) -> None:
        """
        Merges two dictionaries together, where values in the second dictionary
        will be applied to the first dictionary.
        """
        for key, value in dict1.items():
            if isinstance(value, dict) and key in dict2.keys():
                Event._update_values(dict1[key], dict2[key])
            if not isinstance(value, dict) and key in dict2.keys():
                dict1[key] = dict2[key]


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

    profiles = []

    def __init__(self,
                 num_profiles: int = 10,
                 stream: Stream = None,
                 use_profile_file: bool = False,
                 fake: Faker = None):
        self.num_profiles = num_profiles
        self.stream = stream if stream else Stream()
        self.first_events = Event(example_event, profile_example, 1)
        self._dtstamp = None
        self._state_table = []
        self._total_count = 0
        self.profile_filename = 'profiles.json'

        self.fake = fake if fake and \
            isinstance(fake, Faker) else Faker()

        if use_profile_file:
            try:
                with open(self.profile_filename) as profiles_file:
                    profiles_dicts = json.loads(profiles_file.read())
                    self.profiles = [SimpleNamespace(**profiles)
                                     for profiles in profiles_dicts]
            except FileNotFoundError:
                self.create_profiles()

                with open(self.profile_filename, 'w') as profiles_file:
                    profiles_dicts = [vars(item) for item in self.profiles]
                    profiles_file.write(json.dumps(profiles_dicts))
        else:
            self.create_profiles()

    def create_events(self) -> dict:
        """
        Selects a profile to be used, and will request the Event Type
        to process the data if available.
        """

        if not self._state_table:
            self._reset_state_table()

        while self._state_table:
            sindex = randint(0, len(self._state_table)-1)
            pindex = self._state_table[sindex]['pindex']
            eindex = randint(0, len(self._state_table[sindex]['events'])-1)

            remain = self._state_table[sindex]['events'][eindex]['remain']
            event = self._state_table[sindex]['events'][eindex]['event']
            selected_profile = self.profiles[pindex]

            event.event_time = self._dtstamp.isoformat('T') \
                if self._dtstamp else datetime.now().isoformat('T')

            self._total_count += 1
            event.event_id += 1
            yield event(selected_profile)

            if remain is not None:
                self._state_table[sindex]['events'][eindex]['remain'] -= 1
                self._process_state_entry(sindex, eindex)

        print(f"Event limit reached.  {self._total_count} in total generated",
              file=stderr)

    def create_profiles(self) -> None:
        """
        Creates the fake profiles that will be used for event creation.
        """
        result = []

        for _ in range(self.num_profiles):
            gender = choice(('male', 'female'))

            if gender == 'female':
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
                'id': str(self.fake.unique.random_number()),
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
                'blood_group': (choice(["A", "B", "AB", "O"]) +
                                choice(["+", "-"])),
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

            result.append(SimpleNamespace(**profile))
        self.profiles = result

    @property
    def first_events(self) -> list:
        """
        View the first event, or use a statement to set the event.
        """
        return self._first_events

    @first_events.setter
    def first_events(self, events: list) -> None:
        if isinstance(events, Event):
            self._first_events = [events]
        elif not isinstance(events, list):
            raise TypeError("An Event or list of EventTypes is required")
        elif all((isinstance(event, Event) for event in events)):
            self._first_events = events
        else:
            raise TypeError("Events must be only Event Type instances")

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
                sleep(random() * 60/epm)
        except KeyboardInterrupt:
            print(f"\nStopping Event Stream.  {self._total_count} in total generated.",
                  file=stderr)

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
                    print(f"Finish time reached.  {self._total_count} in total generated.",
                          file=stderr)
                    break
                self.stream.send(json.dumps(event, indent=indent))
                self._dtstamp += timedelta(seconds=random() * 60/epm)
        except KeyboardInterrupt:
            print(f"\nStopping Event Batch.  {self._total_count} in total generated.",
                  file=stderr)

    def _reset_state_table(self) -> None:
        self._state_table = [
            {
                'pindex': index,
                'events': [
                    {
                        'remain': event.limit,
                        'event': event
                    } for event in self.first_events
                ]
            }
            for index, _ in enumerate(self.profiles)
        ]

    def _process_state_entry(self, sindex: int, eindex: int) -> None:
        remain = self._state_table[sindex]['events'][eindex]['remain']
        event = self._state_table[sindex]['events'][eindex]['event']

        if remain <= 0 and event.next:
            del self._state_table[sindex]['events'][eindex]
            event_record = [
                {
                    'remain': next_event.limit,
                    'event': next_event
                } for next_event in event.next
            ]
            self._state_table[sindex]['events'].extend(event_record)
        elif remain <= 0:
            del self._state_table[sindex]['events'][eindex]

        if not self._state_table[sindex]['events']:
            del self._state_table[sindex]
