"""
Events module for creating custom types and generating Messages
"""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import md5
import json
from random import randint, random
from sys import stderr

from croniter import croniter
from .handlers import Stream
from .profiles import entries

__all__ = ['Event', 'EventGenerator']


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
            The number of times to process the event. Set to 0 for infinite
            events.
        group_up: bool
            If set to true the next event will occur at the same time when
            using the batch or live_stream methods of the generator.
        cron: str
            If the event is to be set as a scheduled event, the timing the
            event should occur is defined using cron syntax.
    """
    _event_store = {}

    def __init__(self,
                 data: dict,
                 profiler: callable = None,
                 limit: int = 1,
                 group_up: bool = False,
                 cron: str = None):
        self.profiler = profiler
        self.limit = int(limit)
        self.group_up = group_up
        self.cron = cron
        self._data = self._get_data(data)
        self._next_events = None

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}'
                f'({self._data.get("template")}, '
                f'{self.profiler}, limit={self.limit})')

    def __and__(self, other):
        self.next = other
        self.group_up = True
        return other

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
        cls._event_store.clear()

    @classmethod
    def _get_data(cls, template):
        dict_hash = md5(repr(sorted(template.items())).encode()).hexdigest()
        if dict_hash not in cls._event_store:
            cls._event_store[dict_hash] = {"id": 0, "template": template}
        return cls._event_store[dict_hash]

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

    def process(self, index=0, time="") -> dict:
        if index not in self._data:
            self._data[index] = deepcopy(self._data['template'])
        self._data['id'] += 1
        self.data = self._data[index]
        self.time = time
        self.id = self._data['id']

        if callable(self.profiler):
            try:
                returned = self.profiler(self, entries[index])
            except AttributeError as err:
                print(f"ERROR: Please check your profiler function: {err}",
                      file=stderr)
                return
            if returned is None:
                return None
            else:
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
        stream: faker_events.Stream
            Stream handler to use for sending messages
    """

    timezone = None

    def __init__(self, stream: Stream = None):
        self.stream = stream if stream else Stream()
        self._events = []
        self._scheduled = []
        self._dtstamp = None
        self._state_table = []
        self._total_count = 0

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

            if self._dtstamp and self._tzobject:
                event_time = self._dtstamp.astimezone(self.timezone).isoformat()
            elif self._dtstamp:
                event_time = self._dtstamp.isoformat()
            else:
                event_time = datetime.now(self.timezone).isoformat()

            self._skip_sleep = event.group_up
            self._total_count += 1
            yield event.process(pindex, time=event_time)

            if remain > 0 and not remain < 0:
                self._state_table[sindex]['events'][eindex]['remain'] -= 1
                self._process_state_entry(sindex, eindex)

        print(f"Event limit reached.  {self._total_count} in total generated",
              file=stderr)

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

    async def live_stream(self, epm: int = 60, indent: int = None) -> None:
        """
        Produces a live stream of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces
        """
        self._dtstamp = None
        for event in self.create_events():
            self.stream.send(json.dumps(event, indent=indent))
            if not self._skip_sleep:
                await asyncio.sleep(random() * 60/epm)

    @property
    def scheduled_events(self) -> list:
        """
        View the first event, or use a statement to set the event.
        """
        return self._scheduled

    @scheduled_events.setter
    def scheduled_events(self, events: list) -> None:
        if isinstance(events, Event):
            self._scheduled.append(events)
        elif all((isinstance(event, Event) for event in events)):
            self._scheduled.extend(events)
        else:
            raise TypeError("Events must be only Event Type instances")

    @scheduled_events.deleter
    def scheduled_events(self, events: list) -> None:
        if isinstance(events, list):
            for event in events:
                if event in self.scheduled_events:
                    self.scheduled_events.remove(event)
        else:
            if events in self.scheduled_events:
                self.scheduled_events.remove(events)

    async def schedule(self):
        """
        Produces a live stream of timed events.
        """
        self._dtbase = datetime.now()
        await asyncio.sleep((60 - self._dtbase.second) +
                            ((100000 - self._dtbase.microsecond) / 1000000))
        for event in self._scheduled:
            event._croniter = croniter(event.cron, self._dtbase)

        while True:
            current_time = datetime.now()
            for index, profile in enumerate(entries):
                for event in self._scheduled:
                    scheduled_time = event._croniter.get_current(datetime)
                    if current_time >= scheduled_time:
                        result = event.process(index,
                                               profile,
                                               time=current_time.isoformat())
                        if result:
                            self.stream.send(result)
                            self._total_count += 1
                        if (index + 1) == len(entries):
                            event._croniter.get_next()
            await asyncio.sleep(60)

    def batch(self,
              start: datetime,
              finish: datetime,
              epm: int = 60,
              indent: int = None) -> None:
        """
        Produces a batch of randomly timed events. Events per minute can
        be adjust, and if the JSON should have indentation of num spaces.
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

    @classmethod
    def set_timezone(cls, offset: int):
        """
        Timezone offset used for the event time.  Set between -24 and 24,
        0 for UTC or None for local time.
        """
        if isinstance(offset, int):
            try:
                cls.timezone = timezone(timedelta(hours=offset))
            except ValueError:
                print("WARNING: Offset must be between -24 and 24 hours",
                      file=stderr)
        else:
            cls.timezone = None

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
            for index, _ in enumerate(entries)
        ]
        self._total_count = 0
