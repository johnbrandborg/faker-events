"""
Events module for creating custom types and generating Messages
"""

__all__ = ['EventType', 'EventGenerator']

from datetime import datetime, timedelta
import json
import random
import time
import sys

from faker import Faker
from .handlers import Stream

fake = Faker(['en_AU', 'en_NZ'])


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

    def __init__(self, limit: int = None):
        self.limit = limit

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

    def profiled(self, profile: dict) -> dict:
        """
        If implemented the Event Creator will execute this method, and use
        the returned dict.

        The profile can be used for adding details to the event.
        """
        raise NotImplementedError


class ExampleEvent(EventType):
    """
    Example Event if no event is supplied to the Generator
    """
    event = {
        'time': '',
        'type': 'example',
        'id': '',
        'name': '',
    }

    def profiled(self, profile: dict) -> dict:
        updates = {
            'time': profile.get('event_time'),
            'id': profile.get('id'),
            'name': profile.get('first_name'),
        }
        self.event.update(updates)

        return self.event


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
    """

    _events = ExampleEvent()
    _state = []

    def __init__(self,
                 num_profiles: int = 10,
                 stream: Stream = None,
                 use_profile_file: bool = False):
        self.num_profiles = num_profiles

        if use_profile_file:
            try:
                with open('profiles.json') as profiles_file:
                    self.profiles = json.loads(profiles_file.read())
            except FileNotFoundError:
                self.create_profiles()

                with open('profiles.json', 'w') as profiles_file:
                    profiles_file.write(json.dumps(self.profiles))
        else:
            self.create_profiles()

        self.stream = stream if stream else Stream()
        self._dtstamp = None

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

            selected_profile['event_time'] = self._dtstamp.isoformat()\
                if self._dtstamp else datetime.now().isoformat()

            count += 1
            try:
                yield event.profiled(selected_profile)
            except NotImplementedError:
                yield event.event

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
        result = []

        for _ in range(0, self.num_profiles):
            gender = 'F' if random.randint(0, 1) == 1 else 'M'

            if gender == 'F':
                first_name = fake.first_name_female()
                middle_name = fake.first_name_female()
            else:
                first_name = fake.first_name_male()
                middle_name = fake.first_name_male()

            last_name = fake.last_name()

            profile = {
                'id': fake.pyint(),
                'gender': gender,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'date_of_birth': fake.date_of_birth(minimum_age=18,
                                                    maximum_age=80)
                                     .isoformat(),
                'email': f'{first_name}.{last_name}@{fake.domain_name()}',
                'employer_name': fake.company(),
                'job': fake.job(),
            }

            result.append(profile)

        self.profiles = result

    @property
    def events(self):
        """
        View the first event, or use a statement to set the event.
        """
        return self._events

    @events.setter
    def events(self, first_event: EventType):
        if isinstance(first_event, EventType):
            self._event = first_event
        else:
            raise TypeError("Events must be an EventType")

        self._create_state()

    def live_stream(self, epm: int = 60, indent: int = None) -> str:
        """
        Produces a live stream of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """

        self._dtstamp = None

        if not self._state:
            self._create_state()

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
            self._create_state()

        try:
            for event in self.create_events():
                self.stream.send(json.dumps(event, indent=indent))
                self._dtstamp += timedelta(seconds=random.random() * 60/epm)

                if self._dtstamp >= finish:
                    print('Finish time reached', file=sys.stderr)
                    break

        except KeyboardInterrupt:
            print('\nStopping Event Batch', file=sys.stderr)

    def _create_state(self):
        self._state = [[index, self._events.limit, self._events]
                       for index, _ in enumerate(self.profiles)]
