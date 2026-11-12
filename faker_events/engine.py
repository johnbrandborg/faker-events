from __future__ import annotations

import asyncio
import heapq
import random
from collections.abc import Callable, Iterator, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any
from zoneinfo import ZoneInfo

from croniter import croniter

from .models import EventContext, GeneratedEvent, GeneratorConfig, Profile
from .outputs import ConsoleOutput, Output


class _Skip:
    def __repr__(self) -> str:
        return "SKIP"


SKIP = _Skip()
TransformResult = Mapping[str, Any] | _Skip | None
Transform = Callable[[EventContext, Profile], TransformResult]


class Event:
    """A reusable event definition.

    Runtime state belongs to :class:`EventGenerator`, so one definition can be
    safely used by multiple generators.
    """

    def __init__(
        self,
        template: Mapping[str, Any],
        transform: Transform | None = None,
        *,
        limit: int = 1,
        rate: float = 60,
        variance: float = 0.25,
        grouped: bool = False,
        schedule: str | None = None,
        name: str | None = None,
    ) -> None:
        if limit < 0:
            raise ValueError("limit cannot be negative")
        if rate <= 0:
            raise ValueError("rate must be greater than zero")
        if not 0 <= variance <= 1:
            raise ValueError("variance must be between 0 and 1")
        if not all(isinstance(key, str) for key in template):
            raise TypeError("event template keys must be strings")
        if schedule is not None and not croniter.is_valid(schedule):
            raise ValueError(f"invalid cron expression: {schedule}")

        self.template = deepcopy(dict(template))
        self.transform = transform
        self.limit = limit
        self.rate = rate
        self.variance = variance
        self.grouped = grouped
        self.schedule = schedule
        self.name = name or str(template.get("type", "event"))
        self._next: tuple[Event, ...] = ()

    def __repr__(self) -> str:
        return f"Event(name={self.name!r}, limit={self.limit}, rate={self.rate:g})"

    def __rshift__(self, other: Event | Sequence[Event]) -> Event | Sequence[Event]:
        self.then(other)
        return other

    def __and__(self, other: Event | Sequence[Event]) -> Event | Sequence[Event]:
        self.grouped = True
        self.then(other)
        return other

    def then(self, events: Event | Sequence[Event]) -> Event:
        if isinstance(events, Event):
            next_events: tuple[Event, ...] = (events,)
        else:
            next_events = tuple(events)
            if not next_events or not all(isinstance(event, Event) for event in next_events):
                raise TypeError("next events must contain Event instances")
        self._next = next_events
        return self

    @property
    def next_events(self) -> tuple[Event, ...]:
        return self._next

    def delay(self, randomizer: random.Random) -> float:
        base = 60 / self.rate
        if self.grouped:
            return 0
        return randomizer.uniform(base * (1 - self.variance), base * (1 + self.variance))


@dataclass
class _Execution:
    event: Event
    remaining: int


@dataclass
class _ProfileRuntime:
    active: list[_Execution]
    event_data: dict[Event, dict[str, Any]] = field(default_factory=dict)


class EventGenerator:
    """Generate and deliver stateful event flows."""

    def __init__(
        self,
        profiles: Sequence[Profile | Mapping[str, Any]],
        events: Event | Sequence[Event],
        *,
        output: Output | None = None,
        config: GeneratorConfig | None = None,
    ) -> None:
        self.profiles = tuple(
            profile if isinstance(profile, Profile) else Profile.model_validate(profile)
            for profile in profiles
        )
        if not self.profiles:
            raise ValueError("at least one profile is required")
        self.events = (events,) if isinstance(events, Event) else tuple(events)
        if not self.events or not all(isinstance(event, Event) for event in self.events):
            raise TypeError("events must contain Event instances")
        self.output = output or ConsoleOutput()
        self.config = config or GeneratorConfig()
        self._timezone = ZoneInfo(self.config.timezone)
        self._random = random.Random(self.config.seed)
        self._event_ids = count(1)
        self._runtime: list[_ProfileRuntime] = []
        self.reset()

    def reset(self) -> None:
        """Reset flow state and deterministic random generation."""

        flow_events = tuple(event for event in self.events if event.schedule is None)
        self._runtime = [
            _ProfileRuntime([_Execution(event, event.limit) for event in flow_events])
            for _ in self.profiles
        ]
        self._random.seed(self.config.seed)
        self._event_ids = count(1)

    def generate(self, *, start: datetime | None = None) -> Iterator[GeneratedEvent]:
        """Lazily generate unscheduled events without delivering them."""

        current = self._normalize_time(start or datetime.now(self._timezone))
        delivered = 0
        available = [index for index, runtime in enumerate(self._runtime) if runtime.active]

        while available:
            if self.config.max_events is not None and delivered >= self.config.max_events:
                return

            profile_slot = self._random.randrange(len(available))
            profile_index = available[profile_slot]
            runtime = self._runtime[profile_index]
            execution_index = self._random.randrange(len(runtime.active))
            execution = runtime.active[execution_index]
            delay = execution.event.delay(self._random)
            generated = self._process(execution.event, profile_index, current)
            self._advance(runtime, execution_index)
            if not runtime.active:
                available[profile_slot] = available[-1]
                available.pop()

            if generated is not None:
                delivered += 1
                yield GeneratedEvent(
                    data=generated,
                    time=current,
                    delay=delay,
                    grouped=execution.event.grouped,
                )
            current += timedelta(seconds=delay)

    def iter_batch(self, start: datetime, end: datetime) -> Iterator[GeneratedEvent]:
        """Generate random and scheduled events in timestamp order."""

        start = self._normalize_time(start)
        end = self._normalize_time(end)
        if end < start:
            raise ValueError("end must not be before start")

        self.reset()
        sequence = count()
        queue: list[tuple[datetime, int, str, Any]] = []
        random_events = self.generate(start=start)
        next_random = next(random_events, None)
        if next_random is not None and next_random.time <= end:
            heapq.heappush(queue, (next_random.time, next(sequence), "flow", next_random))

        for event in self.events:
            if event.schedule is None:
                continue
            for profile_index in range(len(self.profiles)):
                iterator = croniter(event.schedule, start)
                scheduled_time = self._normalize_time(iterator.get_next(datetime))
                if scheduled_time <= end:
                    state = [event, profile_index, event.limit, iterator]
                    heapq.heappush(queue, (scheduled_time, next(sequence), "schedule", state))

        delivered = 0
        while queue:
            if self.config.max_events is not None and delivered >= self.config.max_events:
                return
            event_time, _, kind, value = heapq.heappop(queue)
            if kind == "flow":
                delivered += 1
                yield value
                next_random = next(random_events, None)
                if next_random is not None and next_random.time <= end:
                    heapq.heappush(queue, (next_random.time, next(sequence), "flow", next_random))
                continue

            event, profile_index, remaining, iterator = value
            data = self._process(event, profile_index, event_time)
            if data is not None:
                delivered += 1
                yield GeneratedEvent(data=data, time=event_time, delay=0)
            if remaining != 1:
                next_time = self._normalize_time(iterator.get_next(datetime))
                if next_time <= end:
                    next_remaining = remaining - 1 if remaining > 1 else 0
                    state = [event, profile_index, next_remaining, iterator]
                    heapq.heappush(queue, (next_time, next(sequence), "schedule", state))

    async def run_live(self) -> int:
        """Deliver events in real time and return the delivered count."""

        self.reset()
        delivered = 0
        delivery_lock = asyncio.Lock()
        stop = asyncio.Event()

        async def deliver(data: dict[str, Any]) -> bool:
            nonlocal delivered
            async with delivery_lock:
                if stop.is_set():
                    return False
                await self.output.send(data)
                delivered += 1
                if self.config.max_events is not None and delivered >= self.config.max_events:
                    stop.set()
                return True

        async def run_flow() -> None:
            for generated in self.generate():
                if stop.is_set() or not await deliver(generated.data):
                    return
                if generated.delay:
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=generated.delay)
                    except TimeoutError:
                        pass

        async def run_schedule(event: Event) -> None:
            remaining = event.limit
            schedule = event.schedule
            if schedule is None:
                return
            iterator = croniter(schedule, datetime.now(self._timezone))
            while not stop.is_set():
                scheduled_time = self._normalize_time(iterator.get_next(datetime))
                delay = max(
                    0,
                    (scheduled_time - datetime.now(self._timezone)).total_seconds(),
                )
                try:
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                    return
                except TimeoutError:
                    pass
                for profile_index in range(len(self.profiles)):
                    data = self._process(event, profile_index, scheduled_time)
                    if data is not None and not await deliver(data):
                        return
                if remaining > 0:
                    remaining -= 1
                    if remaining == 0:
                        return

        await self.output.open()
        try:
            tasks = []
            if any(runtime.active for runtime in self._runtime):
                tasks.append(asyncio.create_task(run_flow()))
            tasks.extend(
                asyncio.create_task(run_schedule(event))
                for event in self.events
                if event.schedule is not None
            )
            if tasks:
                await asyncio.gather(*tasks)
        finally:
            await self.output.close()
        return delivered

    async def run_batch(self, start: datetime, end: datetime) -> int:
        """Deliver a bounded virtual-time batch without sleeping."""

        delivered = 0
        await self.output.open()
        try:
            for generated in self.iter_batch(start, end):
                await self.output.send(generated.data)
                delivered += 1
        finally:
            await self.output.close()
        return delivered

    def _process(
        self,
        event: Event,
        profile_index: int,
        event_time: datetime,
    ) -> dict[str, Any] | None:
        runtime = self._runtime[profile_index]
        data = runtime.event_data.setdefault(event, deepcopy(event.template))
        context = EventContext(
            data=data,
            event_id=next(self._event_ids),
            profile_index=profile_index,
            time=event_time,
        )
        if event.transform is not None:
            result = event.transform(context, self.profiles[profile_index])
            if result is SKIP:
                return None
            if result is not None:
                if not isinstance(result, Mapping):
                    raise TypeError(
                        f"transform for {event.name!r} must return a mapping, SKIP, or None"
                    )
                context.update(result)
        return deepcopy(context.data)

    @staticmethod
    def _advance(runtime: _ProfileRuntime, execution_index: int) -> None:
        execution = runtime.active[execution_index]
        if execution.remaining == 0:
            return
        execution.remaining -= 1
        if execution.remaining > 0:
            return
        runtime.active.pop(execution_index)
        runtime.active.extend(
            _Execution(event=event, remaining=event.limit) for event in execution.event.next_events
        )

    def _normalize_time(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).astimezone(self._timezone)
        return value.astimezone(self._timezone)
