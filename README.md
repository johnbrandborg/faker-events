# Faker Events

[![CI](https://github.com/johnbrandborg/faker-events/actions/workflows/python-app.yml/badge.svg)](https://github.com/johnbrandborg/faker-events/actions/workflows/python-app.yml)
[![PyPI](https://img.shields.io/pypi/v/faker-events.svg)](https://pypi.org/project/faker-events/)
[![Python](https://img.shields.io/pypi/pyversions/faker-events.svg)](https://pypi.org/project/faker-events/)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=faker-events&metric=alert_status&branch=main)](https://sonarcloud.io/summary/new_code?id=faker-events&branch=main)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=faker-events&metric=coverage&branch=main)](https://sonarcloud.io/summary/new_code?id=faker-events&branch=main)
[![License](https://img.shields.io/pypi/l/faker-events.svg)](https://github.com/johnbrandborg/faker-events/blob/main/LICENSE)

Generate realistic, stateful event streams for development, demos, load tests,
and data-pipeline validation—without copying production data.

Version 2 is a ground-up rewrite for Python 3.11+. It provides isolated
generator state, deterministic runs, validated configuration, async delivery,
virtual-time batches, cron schedules, and fast JSON serialization.

## Core concepts

- **Profiles** are people or entities that act independently.
- **State** is persistent data belonging to one profile, such as an account
  balance or status.
- **Activity events** simulate actions performed by people or external actors.
- **Scheduled operations** simulate recurring system work against current
  profile state.
- **Outputs** deliver immutable event snapshots to JSON Lines, Kafka, Kinesis,
  or custom destinations.

See the [v1→v2 regression assessment](docs/v1-v2-regression-assessment.md) for
the complete preserved, improved, intentionally changed, and removed behavior
matrix.

## Install

```shell
pip install faker-events
```

Install only the stream adapters you need:

```shell
pip install "faker-events[kafka]"
pip install "faker-events[kinesis]"
```

## Try it

The built-in example writes JSON Lines to stdout and progress to stderr:

```shell
faker-events run --profiles 10 --max-events 100 --seed 42
```

Persist generated entities across runs:

```shell
faker-events run --profiles 100 --profile-file profiles.json
```

Persist profile mutations made by event transforms:

```shell
faker-events run account_flow.py --profile-file profiles.json --update-profiles
```

Generate a historical batch without sleeping:

```shell
faker-events run \
  --start 2026-01-01T00:00:00+00:00 \
  --end 2026-01-02T00:00:00+00:00
```

## Define a stateful flow

Activity and scheduled events can share explicit state for each profile:

```python
from faker_events import SKIP, Event, EventGenerator, ProfileGenerator, State

profiles = ProfileGenerator(seed=42).create(10)
account = State({"total": 0})


def save(context, _profile):
    context.state["total"] += 110
    return {
        "type": "money.saved",
        "change": 110,
        "total": context.state["total"],
    }


def hourly_fee(context, _profile):
    if context.state["total"] < 10:
        return SKIP
    context.state["total"] -= 10
    return {
        "type": "account.fee",
        "change": -10,
        "total": context.state["total"],
    }


saved = Event({"type": "money.saved"}, save, state=account, limit=0)
fee = Event(
    {"type": "account.fee"},
    hourly_fee,
    state=account,
    schedule="0 * * * *",
    limit=0,
)

generator = EventGenerator(profiles, [saved, fee])
generator.start()
```

`State` is cloned for every profile and generator. Reusing one `State` instance
lets human activity and system operations inspect and mutate the same entity
without leaking state globally.

See [Stateful activity and scheduled operations](docs/state-and-schedules.md)
for detailed semantics, conditional operations, expected output, and a runnable
savings example.

For a v1-style shared event structure, use `State` directly as the template:

```python
account = State({"type": "account", "total": 0})
saved = Event(account, save)
fee = Event(account, hourly_fee, schedule="0 * * * *")
```

Transforms may update `context.data` or `context.state`, return a mapping to
merge into the emitted event, or return `SKIP` to suppress delivery. State
mutations persist even when output is skipped.

Use `event >> next_event` for a sequence and `event >> [a, b]` to branch.
`limit=0` repeats indefinitely. `max_events` bounds processing attempts,
including skipped events, so conditional infinite flows can still terminate.

## Live and batch execution

The synchronous interface is suitable for scripts:

```python
generator.start()
generator.batch(start, end)
```

Async applications can use `await generator.run_live()` and
`await generator.run_batch(start, end)`.

Virtual-time batches do not sleep. Activity and scheduled operations are
processed strictly in timestamp order, so later activity cannot affect an
earlier scheduled operation.

## CLI scripts

The CLI accepts a Python file exposing
`build(profiles, output, *, seed, max_events) -> EventGenerator`:

```shell
faker-events run account_flow.py --profiles 10
```

Runnable examples:

- [`examples/savings.py`](examples/savings.py) — shared account state with
  recurring conditional fees.

## Outputs

```python
from faker_events import KafkaOutput, KinesisOutput

kafka = KafkaOutput("events", "localhost:9092")
kinesis = KinesisOutput("events", partition_key=lambda event: event["customer_id"])
```

Custom outputs implement three async methods:

```python
class Output:
    async def open(self) -> None: ...
    async def send(self, event: dict) -> None: ...
    async def close(self) -> None: ...
```

The included Kinesis adapter batches records. The Kafka adapter uses
`confluent-kafka`/librdkafka and verifies delivery.

## Migration from 1.x

Version 2 intentionally removes global configuration:

- Pass profiles, first events, output, and config to `EventGenerator`.
- Use `start()` and `batch()` from synchronous scripts, or await their
  `run_live()` and `run_batch()` counterparts.
- Wrap a shared structure in `State`, or pass it with `state=`, when activity
  and scheduled events must share persistent per-profile data.
- Use `rate` instead of `epm`; variance is a fraction from `0` to `1`.
- Use `schedule` instead of `cron`.
- Use `ConsoleOutput`, `KafkaOutput`, or `KinesisOutput` instead of `Stream`.
- Return `SKIP` instead of the string `"skip"`.
- `context.id` is an integer rather than a string.
- `context.time` is an aware `datetime`; call `.isoformat()` when the event
  schema requires a string.
- `profile.birthdate` is a `date`; JSON profile files still use ISO strings.
- Event timestamps default to UTC; set an IANA timezone such as
  `Europe/Copenhagen` in `GeneratorConfig` when needed.
- User scripts expose a `build(...)` function instead of mutating class state.

These changes allow multiple independent generators to run safely in one
process.
