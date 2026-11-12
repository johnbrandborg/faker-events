# Migrating from v1

Version 2 is a ground-up rewrite. It retains stateful profiles, event
sequences, random timing, scheduled operations, and streaming outputs while
removing global configuration and implicit shared state.

This guide is an upgrade checklist covering the required API and behavior
changes.

## Requirements

Version 2 supports Python 3.11 through 3.14:

```shell
python -m pip install --upgrade "faker-events>=2,<3"
```

Kafka and Kinesis remain optional:

```shell
python -m pip install "faker-events[kafka]>=2,<3"
python -m pip install "faker-events[kinesis]>=2,<3"
```

## Event arguments

Update renamed and rescaled options:

| v1 | v2 |
|---|---|
| `Event(data, profiler)` | `Event(template, transform)` |
| `epm=60` | `rate=60` |
| `variance=25` | `variance=0.25` |
| `group_up=True` | `grouped=True` |
| `cron="0 * * * *"` | `schedule="0 * * * *"` |
| Return `"skip"` | Return `SKIP` |

Positional transform and limit arguments remain compatible:

```python
event = Event({"type": "payment"}, transform, 3)
```

Prefer keyword arguments for timing and scheduling.

## Generator configuration

Replace class-level setters with constructor arguments.

Version 1:

```python
EventGenerator.set_first_events(first)
EventGenerator.set_scheduled_events(scheduled)
EventGenerator.set_stream(stream)
EventGenerator.set_timezone(2)
generator = EventGenerator(profile_generator)
```

Version 2:

```python
generator = EventGenerator(
    profiles,
    [first, scheduled],
    output=output,
    config=GeneratorConfig(
        timezone="Europe/Copenhagen",
        seed=42,
        max_events=10_000,
    ),
)
```

Configuration is isolated per generator, so independent simulations can run
in the same process.

## Explicit shared state

Version 1 implicitly shared data between equal event dictionaries by hashing
their contents. Version 2 requires one explicit `State`:

```python
account = State({"balance": 0})

deposit = Event(
    {"type": "account.deposit"},
    deposit_money,
    state=account,
)
fee = Event(
    {"type": "account.fee"},
    charge_fee,
    state=account,
    schedule="0 * * * *",
)
```

For the concise v1-style shared event structure:

```python
account = State({"type": "", "balance": 0})
deposit = Event(account, deposit_money)
fee = Event(account, charge_fee, schedule="0 * * * *")
```

Equal ordinary dictionaries no longer share state. This prevents accidental
global state leakage.

`State` lasts for one generator run. Put values on profiles and save them when
they must survive separate runs.

## Transform context

The transform's first argument is now an `EventContext`:

```python
def transform(context, profile):
    context.data["count"] += 1
    return {
        "event_id": context.id,
        "event_time": context.time.isoformat(),
        "user_id": profile.id,
    }
```

Important type changes:

- `context.id` is an integer rather than a string;
- `context.time` is a timezone-aware `datetime` rather than an ISO string;
- `profile.birthdate` is a `date` rather than an ISO string.

Call `.isoformat()` when the emitted schema requires strings.

Returned mappings can add fields and deeply merge nested dictionaries. Return
`None` after direct mutation, or return `SKIP` to suppress output.

## Flow composition

The familiar sequence forms remain:

```python
first >> second >> third
first.next = second
```

Branches and multiple roots remain:

```python
first >> [left, right]
generator = EventGenerator(profiles, [first_flow, second_flow])
```

Use `first & second` for an adjacent successor with the same virtual-time
timestamp.

## Execution

Synchronous methods remain available:

```python
generator.start()
generator.batch(start, end)
```

Async applications can use:

```python
await generator.run_live()
await generator.run_batch(start, end)
```

Batch scheduling is now supported and merged with activity in timestamp order.
The old global `EventGenerator.batch(...)` configuration is replaced by
calling `batch()` on an instance.

## Profiles

Pass profile objects directly to `EventGenerator`:

```python
profile_generator = ProfileGenerator(seed=42)
profiles = profile_generator.load_or_create(100, "profiles.json")
generator = EventGenerator(profiles, events)
```

Profiles are validated Pydantic models that still allow custom mutable fields.
Use `--update-profiles` in the CLI or call `ProfileGenerator.save()` to retain
mutations across runs.

An existing profile file with fewer records than requested now raises an
error rather than silently using fewer profiles.

## Outputs

Replace `Stream` with a concrete output:

```python
output = ConsoleOutput()
output = KafkaOutput("events", "localhost:9092")
output = KinesisOutput("events", partition_key="customer")
```

Custom outputs implement async `open()`, `send()`, and `close()` methods.
Kafka delivery is acknowledged and Kinesis records are batched.

See [Outputs](outputs.md) for installation, configuration, and failure
semantics.

## CLI scripts

Version 1 scripts registered global events as an import side effect. Version 2
scripts expose a builder:

```python
def build(
    profiles,
    output,
    *,
    seed=None,
    max_events=None,
):
    return EventGenerator(
        profiles,
        events,
        output=output,
        config=GeneratorConfig(seed=seed, max_events=max_events),
    )
```

Run it with:

```shell
faker-events run flow.py --profiles 10
```

## Upgrade checklist

- Require Python 3.11 or newer.
- Replace `epm`, percentage variance, `cron`, and `group_up`.
- Replace `"skip"` with `SKIP`.
- Move class-level generator setup into `EventGenerator(...)`.
- Replace implicit equal-dictionary state sharing with `State`.
- Convert context IDs and times where the event schema expects strings.
- Replace `Stream` with an output implementation.
- Change CLI scripts to expose `build(...)`.
- Decide which values are run-scoped `State` and which are durable profile
  fields.
- Add deterministic tests for flow ordering, scheduled conditions, and profile
  persistence.
