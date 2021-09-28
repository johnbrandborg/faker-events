"""
Events module for creating custom types and generating Messages
"""

from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import md5
import json
from random import choice, randint, random
from sys import stderr, exit as sys_exit
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


def profiler_example(event, profile: dict) -> dict:
    return {
        'event_time': event.time,
        'event_id': event.id,
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
        data: dict
            Base data structure used for events.  All values must be declared
            for the automatic value updates to occur.
        profiler: function
            A function that takes the profile dict and merges the values. The
            event can be updated within the function, or return the dict for
            the update to occur automatically.
        limit: int
            The number of times to process the event.
        group_up: bool
            If set to true the next event will occur at the same time when
            using the batch or live_stream methods of the generator.
    """

    _events_data = {}

    def __init__(self,
                 data: dict,
                 profiler: callable = None,
                 limit: int = None,
                 group_up=False):
        self.profiler = profiler
        self.limit = limit
        self.group_up = group_up
        self._data = self._get_data(data)
        self._next_events = None

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}'
                f'({self._data.get("template")}, '
                f'{self.profiler}, limit={self.limit})')

    def __lshift__(self, other):
        self.next = other
        return other

    def __rshift__(self, other):
        self.next = other
        return other

    @classmethod
    def clear(cls):
        """
        The persistant Event Data for all the of the profiles is cleared.
        """
        cls._events_data.clear()

    @classmethod
    def _get_data(cls, template):
        dict_hash = md5(repr(sorted(template.items())).encode()).hexdigest()
        if dict_hash not in cls._events_data:
            cls._events_data[dict_hash] = {"id": 0, "template": template}
        return cls._events_data[dict_hash]

    @property
    def next(self):
        """
        View the next event, or use a statement to set the event.
        """
        return self._next_events

    @next.setter
    def next(self, events) -> None:
        if events is None:
            self._next_events = None
        elif isinstance(events, Event):
            self._next_events = [events]
        elif not isinstance(events, list):
            raise TypeError("An Event or list of EventTypes is required")
        elif all((isinstance(event, Event) for event in events)):
            self._next_events = events
        else:
            raise TypeError("Events must be only Event Type instances")

    def process(self, index=0, profile=None, time=None) -> dict:
        if index not in self._data:
            self._data[index] = deepcopy(self._data['template'])
        self._data['id'] += 1

        self.data = self._data[index]
        self.time = time if time else datetime.now().isoformat("T")
        self.id = self._data['id']

        if callable(self.profiler):
            try:
                returned = self.profiler(self, profile)
            except AttributeError as err:
                print(f"Please check your profiler function: {err}", file=stderr)
                sys_exit(1)
            if returned:
                self._update_values(self.data, returned)

        return self.data

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
        self.first_events = Event(example_event, profiler_example, 1)
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

        Event.clear()

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

            self._skip_sleep = event.group_up
            event_time = self._dtstamp.isoformat('T') if self._dtstamp else None

            self._total_count += 1
            yield event.process(pindex, selected_profile, time=event_time)

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

        for identification in range(self.num_profiles):
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
                'id': identification + 1000,
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
        return self._events

    @first_events.setter
    def first_events(self, events: list) -> None:
        if isinstance(events, Event):
            self._events = [events]
        elif all((isinstance(event, Event) for event in events)):
            self._events = events
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
                if not self._skip_sleep:
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
                if not self._skip_sleep:
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
        self._total_count = 0

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
