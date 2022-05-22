"""
Events module for creating custom types and generating Messages
"""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import md5
from random import randint, random

from croniter import croniter
from .handlers import Stream
from .profiles import ProfileGenerator
from .text_color import eprint, Palatte

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
        epm:
            The estimate of random 'Events Per Minute' that will be created.
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
                 epm: int = 60,
                 group_up: bool = False,
                 cron: str = None):
        self.profiler = profiler
        self.limit = int(limit)
        self.epm = int(epm)
        self.group_up = group_up
        self.cron = cron
        self._data = self._get_data(data)
        self._next_events = None

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}"
                f"({self._data.get('template')}, "
                f"{self.profiler}, limit={self.limit})")

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

    def process(self, index: int, entries: list, time: str) -> tuple:
        """
        Passes the event and profile data to the profiler function.  The
        Profiler function can update the event itself, or return a new Dict
        which is then applied against the event.

        If the string 'skip' is returned by the profiler, in turn the returning
        tuple indicates that delivery should not occur.
        """
        if index not in self._data:
            self._data[index] = deepcopy(self._data['template'])
        self._data['id'] = str(int(self._data['id']) + 1)
        self.data = self._data[index]
        self.time = time
        self.id = self._data['id']

        if callable(self.profiler):
            returned = self.profiler(self, entries[index])

            if isinstance(returned, dict):
                self._update_values(self.data, returned)
            elif returned == 'skip':
                return None, False

        return self.data, True

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
    """

    _stream = Stream()
    _events = []
    _dtstamp = None
    _scheduled = []
    _timezone = None

    def __init__(self, profiles: ProfileGenerator = None):
        if isinstance(profiles, ProfileGenerator):
            self.profiles = profiles
        else:
            self.profiles = ProfileGenerator()
            self.profiles.load()

        self._total_count = 0
        self._state_table = []
        Event.clear()

    @classmethod
    def batch(cls, start: datetime, finish: datetime) -> None:
        """
        Produces a batch of randomly timed events from the given start and
        finish datetime positions.
        """
        cls._dtstamp = start
        cls._dtcutoff = finish

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
            event = self._state_table[sindex]['events'][eindex]['object']

            if self._dtstamp is not None and self._timezone:
                event_time = self._dtstamp \
                                 .astimezone(self._timezone).isoformat()
            elif self._dtstamp is not None:
                event_time = self._dtstamp.isoformat()
            else:
                event_time = datetime.now(self._timezone).isoformat()

            delay = None if event.group_up else random() * 60/event.epm
            yield (*event.process(pindex,
                                  self.profiles.entries,
                                  time=event_time), delay)

            if remain > 0 and not remain < 0:
                self._state_table[sindex]['events'][eindex]['remain'] -= 1
                self._process_state_entry(sindex, eindex)

        eprint(f"Event limit reached.  {self._total_count} in total generated",
               Palatte.BLUE)

    @classmethod
    def set_first_events(cls, events: list, *args) -> None:
        """
        Set the first events that will be placed into the state table.
        """
        if isinstance(events, Event):
            cls._events = [events]
        elif all((isinstance(event, Event) for event in events)):
            cls._events = events
        else:
            raise TypeError("Events must be only Event Type instances")

    @classmethod
    def set_scheduled_events(cls, events: list) -> None:
        """
        Set the scheduled events that will be processed using Cron syntax.
        """
        if isinstance(events, Event):
            cls._scheduled.append(events)
        elif all((isinstance(event, Event) for event in events)):
            cls._scheduled.extend(events)
        else:
            raise TypeError("Events must be only Event Type instances")

    @classmethod
    def set_stream(cls, stream: Stream) -> None:
        """
        Set the Stream to be used for delivering the event.
        """
        if not hasattr(stream, 'send') and not callable(stream.send):
            msg = "Stream must have a callable 'send' method"
            raise NotImplementedError(msg)
        cls._stream = stream

    @classmethod
    def set_timezone(cls, offset: int) -> None:
        """
        Set the Timezone offset used for the event time.  Set between -24 and
        24, 0 for UTC or None for local time.
        """
        if isinstance(offset, int):
            try:
                cls._timezone = timezone(timedelta(hours=offset))
            except ValueError:
                eprint("WARNING: Offset must be between -24 and 24 hours",
                       Palatte.YELLOW)
        else:
            cls._timezone = None

    def start(self):
        """
        Starts the Event Generator in the default Live Stream, or Batch Steam
        if the batch method has been called.
        """
        self._state_table = None

        if self._dtstamp:
            eprint('Starting Batch Steam', Palatte.BLUE)
            self._batch_stream()
        else:
            eprint('Starting Live Stream', Palatte.BLUE)
            asyncio.run(self._live_stream())

    def _batch_stream(self):
        """
        Process both the random and scheduled events without sleeping. This
        allows for data to be producted quickly.
        """
        for response, deliver, delay in self.create_events():
            if deliver:
                self._stream.send(response)
                self._total_count += 1

            if self._dtstamp >= self._dtcutoff:
                eprint("Batch Steam finish datetime reached.  "
                       f"{self._total_count} in total generated",
                       Palatte.BLUE)
                return

            self._dtstamp += timedelta(seconds=delay)

    async def _live_stream(self):
        """
        Runs the both the random, and scheduled tasks in the Async event loop,
        that are placed onto the Event Generator.
        """
        tasks = []
        if EventGenerator._scheduled:
            tasks.append(asyncio.create_task(self._scheduler()))

        if EventGenerator._events:
            tasks.append(asyncio.create_task(self._random()))

        for task in tasks:
            await task

    async def _random(self) -> None:
        """
        Produces randomly timed events on selected profiles.  This method
        effectively has the create_events method perform the state, while
        this method uses the stream handler and performs the random sleeps.
        """
        for response, deliver, delay in self.create_events():
            if deliver:
                self._stream.send(response)
                self._total_count += 1

            await asyncio.sleep(delay)

    def _reset_state_table(self) -> None:
        """
        Resets the state table used, based on the first events set on the
        EventGenerator.  If Faker Events is used interactively in the console
        then multiple runs are possible.
        """
        self._state_table = [
            {
                'pindex': index,
                'events': [
                    {
                        'remain': event.limit,
                        'object': event
                    } for event in self._events
                ]
            }
            for index, _ in enumerate(self.profiles.entries)
        ]
        self._total_count = 0

    async def _scheduler(self):
        """
        Produces timed events that a based on all profiles.  The scheduler
        creates an independent state stable to process, because all scheduler
        events are processed against all profiles, rather than individually.
        """
        entries_count = len(self.profiles.entries)

        # Syncronize to the next 0 seconds on the minute
        self._dtbase = datetime.now()
        await asyncio.sleep(60 - self._dtbase.second)

        schedule = []
        for event in self._scheduled:
            event._croniter = croniter(event.cron, self._dtbase)
            schedule.append({'object': event, 'remain':  event.limit})

        while schedule:
            current_time = datetime.now()
            for index in range(entries_count):
                for event in schedule:
                    scheduled_time = event['object']._croniter \
                                                    .get_current(datetime)

                    if current_time >= scheduled_time:
                        response, deliver = event['object'].process(
                            index,
                            self.profiles.entries,
                            current_time.isoformat())
                        if deliver:
                            self._stream.send(response)
                            self._total_count += 1
                        if index + 1 == entries_count:
                            event['object']._croniter.get_next()

                            if event['object'].limit:
                                event['remain'] -= 1
                                if event['remain'] <= 0:
                                    schedule.remove(event)

            if schedule:
                await asyncio.sleep(60)

        eprint(f"Schedule limit reached.  {self._total_count} in total "
               "generated", Palatte.BLUE)

    def _process_state_entry(self, sindex: int, eindex: int) -> None:
        """
        Updates the state table with new events to be processed if the events
        has another event to process, and the current event have no more
        remaining executions.
        """
        remain = self._state_table[sindex]['events'][eindex]['remain']
        event = self._state_table[sindex]['events'][eindex]['object']

        if remain <= 0 and event.next:
            del self._state_table[sindex]['events'][eindex]
            event_record = [
                {
                    'remain': next_event.limit,
                    'object': next_event
                } for next_event in event.next
            ]
            self._state_table[sindex]['events'].extend(event_record)
        elif remain <= 0:
            del self._state_table[sindex]['events'][eindex]

        if not self._state_table[sindex]['events']:
            del self._state_table[sindex]
