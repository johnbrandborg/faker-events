from __future__ import annotations

import asyncio
import heapq
import random
from collections import deque
from collections.abc import Callable, Iterator, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any
from zoneinfo import ZoneInfo

from croniter import croniter

from .models import EventContext, GeneratedEvent, GeneratorConfig, Profile, State
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
        template: Mapping[str, Any] | State,
        transform: Transform | None = None,
        limit: int = 1,
        *,
        state: State | None = None,
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
        if isinstance(template, State):
            if state is not None and state is not template:
                raise ValueError("state cannot differ when a State is used as the template")
            template_values = template.initial
            state = template
            self._state_as_data = True
        else:
            template_values = template
            self._state_as_data = False
        if not all(isinstance(key, str) for key in template_values):
            raise TypeError("event template keys must be strings")
        if schedule is not None and not croniter.is_valid(schedule):
            raise ValueError(f"invalid cron expression: {schedule}")

        self.template = deepcopy(dict(template_values))
        self.state = state
        self.transform = transform
        self.limit = limit
        self.rate = rate
        self.variance = variance
        self.grouped = grouped
        self.schedule = schedule
        self.name = name or str(template_values.get("type", "event"))
        self._next: tuple[Event, ...] = ()

    def __repr__(self) -> str:
        return f"Event(name={self.name!r}, limit={self.limit}, rate={self.rate:g})"

    def __rshift__(self, other: Event | Sequence[Event]) -> Event | Sequence[Event]:
        self.then(other)
        return other

    def __lshift__(self, other: Event | Sequence[Event]) -> Event | Sequence[Event]:
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

    @property
    def next(self) -> list[Event] | None:
        """Compatibility view of the events that follow this event."""

        return list(self._next) if self._next else None

    @next.setter
    def next(self, events: Event | Sequence[Event] | None) -> None:
        if events is None:
            self._next = ()
        else:
            self.then(events)

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
    shared_state: dict[State, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class _PendingActivity:
    event: Event
    profile_index: int
    profile_slot: int
    execution_index: int
    time: datetime
    delay: float


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
        self._attempts = 0
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
        self._attempts = 0

    def generate(self, *, start: datetime | None = None) -> Iterator[GeneratedEvent]:
        """Lazily generate unscheduled events without delivering them."""

        if not any(runtime.active for runtime in self._runtime):
            self.reset()
        current = self._normalize_time(start or datetime.now(self._timezone))
        available = [index for index, runtime in enumerate(self._runtime) if runtime.active]
        forced: deque[tuple[int, Event]] = deque()

        while available:
            if self._limit_reached:
                return

            pending = self._next_activity(available, forced, current)
            generated = self._process(pending.event, pending.profile_index, current)
            self._complete_activity(pending, available, forced)

            if generated is not None:
                yield GeneratedEvent(
                    data=generated,
                    time=current,
                    delay=pending.delay,
                    grouped=pending.event.grouped,
                )
            current += timedelta(seconds=pending.delay)

    def iter_batch(self, start: datetime, end: datetime) -> Iterator[GeneratedEvent]:
        """Generate random and scheduled events in timestamp order."""

        start = self._normalize_time(start)
        end = self._normalize_time(end)
        if end < start:
            raise ValueError("end must not be before start")

        self.reset()
        sequence = count()
        queue: list[tuple[datetime, int, str, Any]] = []
        available = [index for index, runtime in enumerate(self._runtime) if runtime.active]
        forced: deque[tuple[int, Event]] = deque()
        if available:
            pending = self._next_activity(available, forced, start)
            heapq.heappush(queue, (pending.time, next(sequence), "flow", pending))

        for event in self.events:
            if event.schedule is None:
                continue
            for profile_index in range(len(self.profiles)):
                iterator = croniter(event.schedule, start)
                scheduled_time = self._normalize_time(iterator.get_next(datetime))
                if scheduled_time <= end:
                    state = [event, profile_index, event.limit, iterator]
                    heapq.heappush(queue, (scheduled_time, next(sequence), "schedule", state))

        while queue:
            if self._limit_reached:
                return
            event_time, _, kind, value = heapq.heappop(queue)
            if kind == "flow":
                pending = value
                data = self._process(pending.event, pending.profile_index, event_time)
                self._complete_activity(pending, available, forced)
                if data is not None:
                    yield GeneratedEvent(
                        data=data,
                        time=event_time,
                        delay=pending.delay,
                        grouped=pending.event.grouped,
                    )
                next_time = event_time + timedelta(seconds=pending.delay)
                if available and next_time <= end:
                    next_pending = self._next_activity(available, forced, next_time)
                    heapq.heappush(
                        queue,
                        (next_pending.time, next(sequence), "flow", next_pending),
                    )
                continue

            event, profile_index, remaining, iterator = value
            data = self._process(event, profile_index, event_time)
            if data is not None:
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
                if self._limit_reached:
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
            if self._limit_reached:
                stop.set()

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
                    if self._limit_reached:
                        stop.set()
                        return
                    data = self._process(event, profile_index, scheduled_time)
                    if data is not None and not await deliver(data):
                        return
                    if self._limit_reached:
                        stop.set()
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

    def start(self) -> int:
        """Run a live stream from synchronous code."""

        return _run_sync(self.run_live())

    def batch(self, start: datetime, end: datetime) -> int:
        """Run a virtual-time batch from synchronous code."""

        return _run_sync(self.run_batch(start, end))

    def _next_activity(
        self,
        available: list[int],
        forced: deque[tuple[int, Event]],
        event_time: datetime,
    ) -> _PendingActivity:
        forced_event = None
        if forced:
            profile_index, forced_event = forced.popleft()
            profile_slot = available.index(profile_index)
        else:
            profile_slot = self._random.randrange(len(available))
            profile_index = available[profile_slot]
        runtime = self._runtime[profile_index]
        if forced_event is None:
            execution_index = self._random.randrange(len(runtime.active))
        else:
            execution_index = next(
                index
                for index, execution in enumerate(runtime.active)
                if execution.event is forced_event
            )
        event = runtime.active[execution_index].event
        delay = 0 if forced else event.delay(self._random)
        return _PendingActivity(
            event=event,
            profile_index=profile_index,
            profile_slot=profile_slot,
            execution_index=execution_index,
            time=event_time,
            delay=delay,
        )

    def _complete_activity(
        self,
        pending: _PendingActivity,
        available: list[int],
        forced: deque[tuple[int, Event]],
    ) -> None:
        runtime = self._runtime[pending.profile_index]
        added = self._advance(runtime, pending.execution_index)
        if pending.event.grouped:
            forced.extend((pending.profile_index, event) for event in added)
        if not runtime.active:
            available[pending.profile_slot] = available[-1]
            available.pop()

    def _process(
        self,
        event: Event,
        profile_index: int,
        event_time: datetime,
    ) -> dict[str, Any] | None:
        self._attempts += 1
        runtime = self._runtime[profile_index]
        shared_state = None
        if event.state is not None:
            shared_state = runtime.shared_state.setdefault(
                event.state,
                deepcopy(event.state.initial),
            )
        if event._state_as_data:
            if shared_state is None:
                raise RuntimeError("shared event state was not initialized")
            data = shared_state
        else:
            data = runtime.event_data.setdefault(event, deepcopy(event.template))
        context = EventContext(
            data=data,
            state=shared_state,
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

    @property
    def _limit_reached(self) -> bool:
        return self.config.max_events is not None and self._attempts >= self.config.max_events

    @staticmethod
    def _advance(
        runtime: _ProfileRuntime,
        execution_index: int,
    ) -> tuple[Event, ...]:
        execution = runtime.active[execution_index]
        if execution.remaining == 0:
            return ()
        execution.remaining -= 1
        if execution.remaining > 0:
            return ()
        runtime.active.pop(execution_index)
        runtime.active.extend(
            _Execution(event=event, remaining=event.limit) for event in execution.event.next_events
        )
        return execution.event.next_events

    def _normalize_time(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).astimezone(self._timezone)
        return value.astimezone(self._timezone)


def _run_sync(awaitable: Any) -> int:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    if hasattr(awaitable, "close"):
        awaitable.close()
    raise RuntimeError("synchronous methods cannot run inside an active event loop")
