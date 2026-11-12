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

Generate a historical batch without sleeping:

```shell
faker-events run \
  --start 2026-01-01T00:00:00+00:00 \
  --end 2026-01-02T00:00:00+00:00
```

## Define a flow

Create `checkout.py`:

```python
from typing import Any

from faker_events import (
    Event,
    EventContext,
    EventGenerator,
    GeneratorConfig,
    Output,
    Profile,
)


def build(
    profiles: list[Profile],
    output: Output,
    *,
    seed: int | None = None,
    max_events: int | None = None,
) -> EventGenerator:
    template: dict[str, Any] = {
        "type": "",
        "event_id": 0,
        "event_time": "",
        "customer_id": "",
        "total": 0,
    }

    def created(context: EventContext, profile: Profile) -> dict[str, Any]:
        return {
            "type": "cart.created",
            "event_id": context.id,
            "event_time": context.time.isoformat(),
            "customer_id": profile.id,
        }

    def checked_out(context: EventContext, profile: Profile) -> dict[str, Any]:
        return {
            "type": "cart.checked_out",
            "event_id": context.id,
            "event_time": context.time.isoformat(),
            "total": 99,
        }

    cart = Event(template, created, rate=120)
    checkout = Event(template, checked_out, rate=30)
    cart >> checkout

    return EventGenerator(
        profiles,
        cart,
        output=output,
        config=GeneratorConfig(seed=seed, max_events=max_events),
    )
```

Run it:

```shell
faker-events run checkout.py --profiles 10
```

Transforms may update `context.data` directly, return a mapping to merge, or
return `SKIP` to suppress delivery. Data is stateful per event and profile.
Use `event >> next_event` for a sequence and `event >> [a, b]` to branch.
`limit=0` repeats indefinitely.

## Scheduled events

Cron events run alongside flow events:

```python
snapshot = Event(
    {"type": "account.snapshot"},
    schedule="*/5 * * * *",
    limit=0,
)

generator = EventGenerator(profiles, [cart, snapshot], output=output)
```

Schedules also work in virtual-time batches and are emitted in timestamp order.

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
- Await `run_live()` or `run_batch()` instead of calling `start()`.
- Use `rate` instead of `epm`; variance is a fraction from `0` to `1`.
- Use `schedule` instead of `cron`.
- Use `ConsoleOutput`, `KafkaOutput`, or `KinesisOutput` instead of `Stream`.
- Return `SKIP` instead of the string `"skip"`.
- User scripts expose a `build(...)` function instead of mutating class state.

These changes allow multiple independent generators to run safely in one
process.
