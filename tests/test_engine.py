from datetime import UTC, datetime

import pytest

import faker_events
from faker_events import (
    SKIP,
    Event,
    EventContext,
    EventGenerator,
    GeneratorConfig,
    MemoryOutput,
    Profile,
    State,
)


@pytest.fixture
def profiles() -> list[Profile]:
    return [
        Profile(id="1000", name="Ada"),
        Profile(id="1001", name="Grace"),
    ]


def test_v2_root_exports_remain_available() -> None:
    assert set(faker_events.__all__) == {
        "SKIP",
        "ConsoleOutput",
        "Event",
        "EventContext",
        "EventGenerator",
        "GeneratedEvent",
        "GeneratorConfig",
        "KafkaOutput",
        "KinesisOutput",
        "MemoryOutput",
        "Output",
        "Profile",
        "ProfileGenerator",
        "State",
        "__version__",
    }


def test_event_configuration_is_validated() -> None:
    assert repr(Event({"type": "created"})) == "Event(name='created', limit=1, rate=60)"
    with pytest.raises(ValueError, match="rate"):
        Event({}, rate=0)
    with pytest.raises(ValueError, match="limit"):
        Event({}, limit=-1)
    with pytest.raises(ValueError, match="variance"):
        Event({}, variance=2)
    with pytest.raises(ValueError, match="cron"):
        Event({}, schedule="not cron")
    with pytest.raises(TypeError, match="keys"):
        Event({1: "invalid"})  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError, match="state keys"):
        State({1: "invalid"})  # ty: ignore[invalid-argument-type]


def test_event_chaining_rejects_invalid_values() -> None:
    event = Event({})
    with pytest.raises(TypeError, match="Event"):
        event.then([])
    with pytest.raises(TypeError, match="Event"):
        event.then(["invalid"])  # ty: ignore[invalid-argument-type]


def test_event_context_deeply_merges_values() -> None:
    context = EventContext(
        data={"nested": {"one": 1}},
        event_id=1,
        profile_index=0,
        time=datetime.now(UTC),
    )

    context.update({"nested": {"two": 2}})

    assert context.data == {"nested": {"one": 1, "two": 2}}


def test_flow_is_stateful_per_profile(profiles: list[Profile]) -> None:
    def increment(context, profile):
        return {
            "event_id": context.id,
            "profile_id": profile.id,
            "value": context.data["value"] + 1,
        }

    first = Event({"type": "first", "value": 0}, increment, rate=60, variance=0)
    second = Event({"type": "second", "value": 0}, increment, limit=2, rate=60, variance=0)
    first >> second
    generator = EventGenerator(profiles, first, config=GeneratorConfig(seed=10))

    generated = list(generator.generate(start=datetime(2025, 1, 1, tzinfo=UTC)))

    assert len(generated) == 6
    values_by_profile: dict[str, list[int]] = {"1000": [], "1001": []}
    for item in generated:
        values_by_profile[item.data["profile_id"]].append(item.data["value"])
    assert values_by_profile == {"1000": [1, 1, 2], "1001": [1, 1, 2]}


def test_grouped_successor_cannot_be_displaced_by_another_profile(
    profiles: list[Profile],
) -> None:
    def identify(event_type):
        return lambda context, profile: {
            "type": event_type,
            "profile_id": profile.id,
            "time": context.time.isoformat(),
        }

    first = Event({"type": "first"}, identify("first"))
    second = Event({"type": "second"}, identify("second"))
    first & second
    generator = EventGenerator(profiles, first, config=GeneratorConfig(seed=4))

    events = list(generator.generate(start=datetime(2025, 1, 1, tzinfo=UTC)))

    for index in range(0, len(events), 2):
        grouped = events[index : index + 2]
        assert [item.data["type"] for item in grouped] == ["first", "second"]
        assert grouped[0].data["profile_id"] == grouped[1].data["profile_id"]
        assert grouped[0].time == grouped[1].time


def test_grouped_successor_stays_adjacent_to_parent_in_scheduled_batch(
    profiles: list[Profile],
) -> None:
    prelude = Event({"type": "prelude"}, rate=1, variance=0)
    first = Event({"type": "first"})
    second = Event({"type": "second"})
    prelude >> first
    first & second
    scheduled = Event(
        {"type": "scheduled"},
        schedule="* * * * *",
        limit=1,
    )
    generator = EventGenerator(profiles[:1], [prelude, scheduled])
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(generator.iter_batch(start, start.replace(minute=1)))

    assert [event.data["type"] for event in events] == [
        "prelude",
        "scheduled",
        "first",
        "second",
    ]
    assert events[-2].time == events[-1].time


def test_generators_do_not_share_event_state(profiles: list[Profile]) -> None:
    event = Event({"count": 0}, lambda context, _: {"count": context.data["count"] + 1})

    first = list(EventGenerator(profiles[:1], event).generate())
    second = list(EventGenerator(profiles[:1], event).generate())

    assert first[0].data["count"] == second[0].data["count"] == 1


def test_events_share_explicit_state_per_profile(profiles: list[Profile]) -> None:
    account = State({"total": 0})

    def save(context, profile):
        context.state["total"] += 10 if profile.id == "1000" else 110
        return {
            "type": "saved",
            "profile_id": profile.id,
            "total": context.state["total"],
        }

    first = Event({"type": "saved"}, save, state=account)
    second = Event({"type": "saved"}, save, state=account)
    first >> second

    events = list(EventGenerator(profiles, first, config=GeneratorConfig(seed=1)).generate())

    totals: dict[str, list[int]] = {"1000": [], "1001": []}
    for event in events:
        totals[event.data["profile_id"]].append(event.data["total"])
    assert totals == {"1000": [10, 20], "1001": [110, 220]}


def test_shared_state_does_not_leak_between_generators(profiles: list[Profile]) -> None:
    account = State({"total": 0})

    def save(context, _profile):
        context.state["total"] += 10
        return {"total": context.state["total"]}

    event = Event({"type": "saved"}, save, state=account)

    first = list(EventGenerator(profiles[:1], event).generate())
    second = list(EventGenerator(profiles[:1], event).generate())

    assert first[0].data["total"] == second[0].data["total"] == 10


def test_state_can_be_used_as_v1_style_event_template(profiles: list[Profile]) -> None:
    account = State({"type": "account", "profile_id": "", "total": 0})

    def save(context, profile):
        context.data["total"] += 10
        context.data["profile_id"] = profile.id

    first = Event(account, save)
    second = Event(account, save)
    first >> second

    events = list(EventGenerator(profiles, first).generate())
    repeated = list(EventGenerator(profiles[:1], first).generate())

    totals: dict[str, list[int]] = {"1000": [], "1001": []}
    for event in events:
        totals[event.data["profile_id"]].append(event.data["total"])
    assert totals == {"1000": [10, 20], "1001": [10, 20]}
    assert [event.data["total"] for event in repeated] == [10, 20]


def test_skip_omits_delivery_and_advances_flow(profiles: list[Profile]) -> None:
    skipped = Event({"type": "skip"}, lambda _context, _profile: SKIP)
    delivered = Event({"type": "delivered"})
    skipped >> delivered

    events = list(EventGenerator(profiles[:1], skipped).generate())

    assert [event.data["type"] for event in events] == ["delivered"]


def test_mutations_before_skip_are_visible_to_next_event(
    profiles: list[Profile],
) -> None:
    account = State({"total": 0})

    def skipped(context, profile):
        context.data["local"] = "changed"
        context.state["total"] = 10
        profile.name = "changed"
        return SKIP

    def inspect(context, profile):
        return {
            "local": context.data.get("local"),
            "total": context.state["total"],
            "profile_name": profile.name,
        }

    first = Event(account, skipped)
    second = Event(account, inspect)
    first >> second

    events = list(EventGenerator(profiles[:1], first).generate())

    assert events[0].data == {
        "total": 10,
        "local": "changed",
        "profile_name": "changed",
    }


def test_transform_must_return_supported_value(profiles: list[Profile]) -> None:
    event = Event(
        {},
        lambda _context, _profile: "invalid",  # ty: ignore[invalid-argument-type]
    )

    with pytest.raises(TypeError, match="mapping"):
        list(EventGenerator(profiles[:1], event).generate())


def test_max_events_bounds_infinite_flow(profiles: list[Profile]) -> None:
    event = Event({"type": "repeat"}, limit=0, grouped=True)
    generator = EventGenerator(
        profiles[:1],
        event,
        config=GeneratorConfig(seed=1, max_events=3),
    )

    assert len(list(generator.generate())) == 3


def test_max_events_bounds_infinite_skipped_flow(profiles: list[Profile]) -> None:
    attempts = 0

    def always_skip(_context, _profile):
        nonlocal attempts
        attempts += 1
        return SKIP

    event = Event({"type": "repeat"}, always_skip, limit=0, grouped=True)
    generator = EventGenerator(
        profiles[:1],
        event,
        config=GeneratorConfig(seed=1, max_events=3),
    )

    assert list(generator.generate()) == []
    assert attempts == 3


def test_batch_merges_scheduled_and_flow_events(profiles: list[Profile]) -> None:
    flow = Event({"type": "flow"}, rate=1, variance=0)
    scheduled = Event(
        {"type": "scheduled"},
        schedule="* * * * *",
        limit=2,
    )
    generator = EventGenerator(profiles[:1], [flow, scheduled])
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(
        generator.iter_batch(
            start,
            datetime(2025, 1, 1, 0, 2, tzinfo=UTC),
        )
    )

    assert [event.data["type"] for event in events] == [
        "flow",
        "scheduled",
        "scheduled",
    ]
    assert [event.time.minute for event in events] == [0, 1, 2]


def test_scheduled_event_checks_and_mutates_activity_state_in_time_order(
    profiles: list[Profile],
) -> None:
    account = State({"total": 0})

    def save(context, _profile):
        context.state["total"] += 100
        return {"type": "saved", "total": context.state["total"]}

    def hourly_fee(context, _profile):
        if context.state["total"] < 10:
            return SKIP
        context.state["total"] -= 10
        return {"type": "fee", "total": context.state["total"]}

    activity = Event(
        {"type": "saved", "total": 0},
        save,
        state=account,
        limit=2,
        rate=0.5,
        variance=0,
    )
    scheduled = Event(
        {"type": "fee", "total": 0},
        hourly_fee,
        state=account,
        schedule="* * * * *",
        limit=1,
    )
    generator = EventGenerator(profiles[:1], [activity, scheduled])
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(generator.iter_batch(start, start.replace(minute=2)))

    assert [(event.data["type"], event.data["total"]) for event in events] == [
        ("saved", 100),
        ("fee", 90),
        ("saved", 190),
    ]


def test_saved_total_trickles_down_as_scheduled_fees_run(
    profiles: list[Profile],
) -> None:
    account = State({"type": "", "change": 0, "total": 0})

    def save(amount):
        def transform(context, _profile):
            context.data["total"] += amount
            return {
                "type": "saved",
                "change": amount,
                "total": context.data["total"],
            }

        return transform

    def fee(context, _profile):
        if context.data["total"] < 10:
            return SKIP
        context.data["total"] -= 10
        return {
            "type": "fee",
            "change": -10,
            "total": context.data["total"],
        }

    saved_ten = Event(account, save(10), grouped=True)
    saved_more = Event(account, save(110))
    saved_ten >> saved_more
    hourly_fee = Event(
        account,
        fee,
        schedule="* * * * *",
        limit=2,
    )
    generator = EventGenerator(profiles[:1], [saved_ten, hourly_fee])
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(generator.iter_batch(start, start.replace(minute=2)))

    assert [
        (event.data["type"], event.data["change"], event.data["total"]) for event in events
    ] == [
        ("saved", 10, 10),
        ("saved", 110, 120),
        ("fee", -10, 110),
        ("fee", -10, 100),
    ]


def test_scheduled_event_skips_when_shared_state_condition_is_not_met(
    profiles: list[Profile],
) -> None:
    account = State({"total": 0})
    activity = Event(
        {"type": "saved"},
        lambda context, _profile: {"total": context.state["total"]},
        state=account,
    )
    scheduled = Event(
        {"type": "fee"},
        lambda context, _profile: SKIP if context.state["total"] < 10 else None,
        state=account,
        schedule="* * * * *",
        limit=1,
    )
    generator = EventGenerator(profiles[:1], [activity, scheduled])
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(generator.iter_batch(start, start.replace(minute=1)))

    assert [event.data["type"] for event in events] == ["saved"]


def test_schedule_limit_counts_ticks_for_every_profile(
    profiles: list[Profile],
) -> None:
    scheduled = Event(
        {"type": "snapshot"},
        lambda _context, profile: {"profile_id": profile.id},
        schedule="* * * * *",
        limit=2,
    )
    generator = EventGenerator(profiles, scheduled)
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(generator.iter_batch(start, start.replace(minute=3)))

    assert len(events) == 4
    assert [event.time.minute for event in events] == [1, 1, 2, 2]
    assert sorted(event.data["profile_id"] for event in events) == [
        "1000",
        "1000",
        "1001",
        "1001",
    ]


def test_batch_rejects_reversed_range(profiles: list[Profile]) -> None:
    generator = EventGenerator(profiles[:1], Event({}))
    start = datetime(2025, 1, 2, tzinfo=UTC)
    end = datetime(2025, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="end"):
        list(generator.iter_batch(start, end))


def test_batch_does_not_process_activity_after_end(profiles: list[Profile]) -> None:
    attempts = 0

    def mutate(_context, profile):
        nonlocal attempts
        attempts += 1
        profile.name = f"changed-{attempts}"

    event = Event(
        {"type": "activity"},
        mutate,
        limit=2,
        rate=1,
        variance=0,
    )
    generator = EventGenerator(profiles[:1], event)
    start = datetime(2025, 1, 1, tzinfo=UTC)

    list(generator.iter_batch(start, start))

    assert attempts == 1
    assert profiles[0].name == "changed-1"


def test_scheduled_event_observes_isolated_profile_mutations(
    profiles: list[Profile],
) -> None:
    def activity(_context, profile):
        profile.name = f"active-{profile.id}"

    def snapshot(_context, profile):
        return {"profile_id": profile.id, "profile_name": profile.name}

    changed = Event(
        {"type": "activity"},
        activity,
        rate=120,
        variance=0,
    )
    scheduled = Event(
        {"type": "snapshot"},
        snapshot,
        schedule="* * * * *",
        limit=1,
    )
    generator = EventGenerator(profiles, [changed, scheduled])
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    events = list(generator.iter_batch(start, start.replace(minute=1)))
    snapshots = [event.data for event in events if event.data["type"] == "snapshot"]

    assert snapshots == [
        {
            "type": "snapshot",
            "profile_id": "1000",
            "profile_name": "active-1000",
        },
        {
            "type": "snapshot",
            "profile_id": "1001",
            "profile_name": "active-1001",
        },
    ]


@pytest.mark.asyncio
async def test_run_batch_delivers_to_async_output(profiles: list[Profile]) -> None:
    output = MemoryOutput()
    generator = EventGenerator(profiles, Event({"type": "test"}), output=output)
    start = datetime(2025, 1, 1, tzinfo=UTC)

    delivered = await generator.run_batch(start, start)

    assert delivered == 1
    assert output.events == [{"type": "test"}]


@pytest.mark.asyncio
async def test_run_live_delivers_grouped_flow_without_sleep(
    profiles: list[Profile],
) -> None:
    output = MemoryOutput()
    first = Event({"type": "first"}, grouped=True)
    second = Event({"type": "second"})
    first >> second
    generator = EventGenerator(profiles[:1], first, output=output)

    delivered = await generator.run_live()

    assert delivered == 2
    assert [event["type"] for event in output.events] == ["first", "second"]


def test_synchronous_start_and_batch_interfaces(profiles: list[Profile]) -> None:
    live_output = MemoryOutput()
    live = EventGenerator(
        profiles[:1],
        Event({"type": "live"}, grouped=True),
        output=live_output,
    )

    assert live.start() == 1
    assert live_output.events == [{"type": "live"}]

    batch_output = MemoryOutput()
    batch = EventGenerator(
        profiles[:1],
        Event({"type": "batch"}),
        output=batch_output,
    )
    start = datetime(2025, 1, 1, tzinfo=UTC)

    assert batch.batch(start, start) == 1
    assert batch_output.events == [{"type": "batch"}]
