# Testing event flows

Faker Events can test a flow without sleeping or connecting to an external
system. Use fixed profiles, a fixed start time, deterministic seeds, and
in-memory output.

## Test generation directly

`generate()` yields events without opening an output:

```python
from datetime import UTC, datetime

from faker_events import Event, EventGenerator, GeneratorConfig, Profile


def test_sign_in_flow():
    profiles = [Profile(id="1000", name="Ada")]
    event = Event(
        {"type": "user.signed_in"},
        lambda context, profile: {
            "event_id": context.id,
            "user_id": profile.id,
        },
        limit=2,
        rate=60,
        variance=0,
    )
    generator = EventGenerator(
        profiles,
        event,
        config=GeneratorConfig(seed=42),
    )

    generated = list(
        generator.generate(start=datetime(2026, 1, 1, tzinfo=UTC))
    )

    assert [item.data["event_id"] for item in generated] == [1, 2]
    assert [item.data["user_id"] for item in generated] == ["1000", "1000"]
    assert [item.time.second for item in generated] == [0, 1]
```

This is the smallest test surface when delivery behavior is irrelevant.

## Test a virtual-time batch

`iter_batch()` merges activity and schedules without sleeping:

```python
events = list(generator.iter_batch(start, end))

assert [event.data["type"] for event in events] == [
    "money.saved",
    "account.fee",
]
assert events == sorted(events, key=lambda event: event.time)
```

Use aware datetimes and a narrow range so expected cron occurrences are
obvious.

## Test delivered output

`MemoryOutput` captures deep-copy snapshots:

```python
from faker_events import MemoryOutput


def test_batch_delivery():
    output = MemoryOutput()
    generator = EventGenerator(profiles, event, output=output)

    delivered = generator.batch(start, end)

    assert delivered == len(output.events)
    assert output.events == [{"type": "account.opened"}]
```

For async application code:

```python
import pytest


@pytest.mark.asyncio
async def test_async_delivery():
    output = MemoryOutput()
    generator = EventGenerator(profiles, event, output=output)

    delivered = await generator.run_batch(start, end)

    assert delivered == len(output.events)
```

## Make randomness reproducible

Use both profile and generator seeds:

```python
profiles = ProfileGenerator(seed=42).create(10)
generator = EventGenerator(
    profiles,
    events,
    config=GeneratorConfig(seed=42),
)
```

Also fix the batch or generation start time. A seed cannot make
`datetime.now()` reproducible.

`variance=0` is useful when a test cares about exact activity timestamps.
Keep nonzero variance when the test should cover deterministic random jitter.

## Test state isolation

Verify state per profile rather than only checking the total event count:

```python
totals: dict[str, list[int]] = {"1000": [], "1001": []}
for generated in generator.generate(start=start):
    totals[generated.data["user_id"]].append(generated.data["total"])

assert totals == {
    "1000": [10, 20],
    "1001": [10, 20],
}
```

When event definitions are reused, create two generators and assert that the
second starts from the same initial state as the first.

## Test conditional schedules

Cover both sides of a scheduled condition:

```python
def charge_fee(context, _profile):
    if context.state["balance"] < 10:
        return SKIP
    context.state["balance"] -= 10
    return {"balance": context.state["balance"]}
```

Use one case where the balance is insufficient and no event is emitted, and a
second where prior activity makes the condition true. Assert both the emitted
events and final values.

Remember that skipped attempts consume limits and count toward `max_events`.

## Bound infinite flows

Tests should never rely on external cancellation:

```python
generator = EventGenerator(
    profiles,
    Event({"type": "heartbeat"}, limit=0),
    config=GeneratorConfig(seed=42, max_events=5),
)

assert len(list(generator.generate(start=start))) == 5
```

This also safely bounds infinite flows that always return `SKIP`.

## Test profile persistence

Use a temporary file to verify mutations survive serialization:

```python
def test_profile_mutation_round_trip(tmp_path):
    path = tmp_path / "profiles.json"
    profile_generator = ProfileGenerator(seed=42)
    profiles = profile_generator.create(1)

    EventGenerator(profiles, event).batch(start, end)
    profile_generator.save(path)

    loaded = ProfileGenerator().load(path)
    assert loaded[0].session_event_count == 1
```

CLI flows can be exercised with Typer's `CliRunner`, which is how the built-in
CLI examples are tested.

## Test custom outputs

Inject fake clients into destination adapters or implement a recording output.
Test these lifecycle cases:

- `open()` prepares the destination;
- `send()` serializes and delivers the expected event;
- delivery failures are propagated;
- `close()` flushes buffered records;
- partial batch failures follow the application's retry policy.

Avoid requiring real Kafka or AWS services in unit tests. Reserve those for a
separate integration-test suite.
