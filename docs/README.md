# Faker Events documentation

Start with the project [README](../README.md) for installation and a complete
stateful example.

## User guides

- [Events and flows](events-and-flows.md) — event options, transforms,
  sequences, branches, grouping, limits, and lazy generation.
- [Event timing](event-timing.md) — per-event rates, random variance, live and
  virtual-time behavior, and deterministic timing.
- [State lifecycle and persistence](state-lifecycle.md) — generator-scoped
  state, reset boundaries, durable profile fields, and multi-day simulations.
- [Scheduled operations](scheduling.md) — cron behavior, conditional system
  work, per-profile ticks, batching, and timezones.
- [Profiles](profiles.md) — generated fields, locales, custom fields, JSON
  persistence, and event mutations.
- [Outputs](outputs.md) — console, memory, Kafka, Kinesis, custom outputs, and
  delivery failure behavior.
- [Command-line interface](cli.md) — all CLI options, user scripts, batches,
  profile files, and common errors.
- [Testing event flows](testing.md) — deterministic tests, virtual time,
  `MemoryOutput`, state isolation, and destination testing.

## Examples

- [Stateful savings example](../examples/savings.py) — activity shares account
  state with conditional scheduled fees.
- [Stateful activity and scheduled operations](state-and-schedules.md) —
  walkthrough and expected savings output.

## Upgrading

- [Migrating from v1](migrating-from-v1.md) — task-oriented upgrade checklist
  and before/after APIs.
- [v1→v2 regression assessment](v1-v2-regression-assessment.md) — complete
  preserved, restored, improved, changed, and unsupported behavior matrix.

## API overview

The public API is imported from `faker_events`:

```python
from faker_events import (
    SKIP,
    ConsoleOutput,
    Event,
    EventContext,
    EventGenerator,
    GeneratedEvent,
    GeneratorConfig,
    KafkaOutput,
    KinesisOutput,
    MemoryOutput,
    Output,
    Profile,
    ProfileGenerator,
    State,
)
```

The guides above document the constructor options and lifecycle of each public
type.
