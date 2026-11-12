from datetime import UTC, datetime

import pytest

from faker_events import (
    SKIP,
    Event,
    EventContext,
    EventGenerator,
    GeneratorConfig,
    MemoryOutput,
    Profile,
)


@pytest.fixture
def profiles() -> list[Profile]:
    return [
        Profile(id="1000", name="Ada"),
        Profile(id="1001", name="Grace"),
    ]


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


def test_generators_do_not_share_event_state(profiles: list[Profile]) -> None:
    event = Event({"count": 0}, lambda context, _: {"count": context.data["count"] + 1})

    first = list(EventGenerator(profiles[:1], event).generate())
    second = list(EventGenerator(profiles[:1], event).generate())

    assert first[0].data["count"] == second[0].data["count"] == 1


def test_skip_omits_delivery_and_advances_flow(profiles: list[Profile]) -> None:
    skipped = Event({"type": "skip"}, lambda _context, _profile: SKIP)
    delivered = Event({"type": "delivered"})
    skipped >> delivered

    events = list(EventGenerator(profiles[:1], skipped).generate())

    assert [event.data["type"] for event in events] == ["delivered"]


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


def test_batch_rejects_reversed_range(profiles: list[Profile]) -> None:
    generator = EventGenerator(profiles[:1], Event({}))
    start = datetime(2025, 1, 2, tzinfo=UTC)
    end = datetime(2025, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="end"):
        list(generator.iter_batch(start, end))


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
