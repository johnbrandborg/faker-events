"""
Events Module
"""

from datetime import datetime
import json
import random
import time

from faker import Faker

from .handlers import Stream

fake = Faker(['en_AU', 'en_NZ'])

__all__ = ['EventType', 'EventGenerator']


class EventType():
    """
    Base Class for new Event Types
    """

    _next_event = None

    def __init__(self, limit: int = None):
        self.limit = limit

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

    def profiled(self, profile: dict ) -> dict:
        """
        If implemented the Event Creator will execute this
        method, and use the returned dict.
        """
        raise NotImplementedError


class ExampleEvent(EventType):
    """
    Example Event if no even is supplied
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
    """

    _events = {}
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
        self.events = ExampleEvent()

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
            selected_profile['event_time'] = datetime.now().isoformat()

            try:
                result = event.profiled(selected_profile)
            except NotImplementedError:
                result = event.event

            count += 1
            yield result

            try:
                self._state[sindex][1] -= 1

                if self._state[sindex][1] == 0 and event.next is None:
                    del self._state[sindex]
                elif self._state[sindex][1] == 0:
                    self._state[sindex][1] = event.next.limit
                    self._state[sindex][2] = event.next
            except TypeError:
                pass

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
                                                    maximum_age=80)\
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
        self._event = first_event
        self._state = [[index, first_event.limit, first_event]
                       for index, _ in enumerate(self.profiles)]

    def live_stream(self, epm: int = 60, indent: int = None) -> str:
        """
        Produces a live stream of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """
        try:
            for event in self.create_events():
                self.stream.send(json.dumps(event, indent=indent))
                time.sleep(random.random() * 60/epm)
        except KeyboardInterrupt:
            print('\nStopping Event Stream')
