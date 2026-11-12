# Event timing

Each activity event controls its own timing with `rate` and `variance`:

```python
from faker_events import Event

page_view = Event(
    {"type": "page.viewed"},
    rate=120,
    variance=0.20,
    limit=0,
)
checkout = Event(
    {"type": "checkout.completed"},
    rate=6,
    variance=0.50,
    limit=0,
)
```

This lets one flow mix frequent activity with rarer activity. Whenever the
generator selects an event, that event's timing configuration determines the
delay before the next activity.

## Rate

`rate` expresses the activity pace as events per minute. The base delay is:

```text
base delay in seconds = 60 / rate
```

Examples:

| `rate` | Base delay |
|---:|---:|
| `120` | 0.5 seconds |
| `60` | 1 second |
| `12` | 5 seconds |
| `1` | 60 seconds |

`rate` must be greater than zero. It controls timing, not how many times an
event runs. Use `limit` for the number of occurrences.

It does not start an independent clock for every event definition. The
generator selects from the currently active events, then uses the selected
event's rate to calculate the next delay. With multiple active flows, the
observed frequency of each event type also depends on selection, profiles,
limits, and chaining.

## Variance

`variance` adds uniform random jitter around the base delay. It is a fraction
from `0` to `1`:

```text
minimum delay = base delay × (1 - variance)
maximum delay = base delay × (1 + variance)
```

For example, `rate=60, variance=0.25` produces a random delay from 0.75 to
1.25 seconds. Set `variance=0` for a fixed delay.

Version 1 used whole percentages, so v1's `variance=25` becomes
`variance=0.25` in v2.

## Live and batch execution

Live generation sleeps for each activity delay:

```python
generator.start()
# or
await generator.run_live()
```

Virtual-time batches use the same delays to calculate event timestamps but do
not sleep:

```python
generator.batch(start, end)
# or
await generator.run_batch(start, end)
```

An activity is emitted at the current time. Its calculated delay advances the
clock before the next activity.

## Reproducible timing

Set `GeneratorConfig.seed` to reproduce activity selection and random delays:

```python
from faker_events import EventGenerator, GeneratorConfig

generator = EventGenerator(
    profiles,
    events,
    config=GeneratorConfig(seed=42),
)
```

The same profiles, events, configuration, start time, and seed produce the
same virtual-time activity sequence.

## Grouped events

Grouped events occur together without a delay between them:

```python
cart_created & item_added
```

Both events receive the same timestamp in a virtual-time batch. Setting
`grouped=True` directly also removes that event's activity delay.

## Scheduled operations

Scheduled events use their cron expression instead of `rate` and `variance`:

```python
expire_sessions = Event(
    {"type": "sessions.expired"},
    expire,
    schedule="0 * * * *",
    limit=0,
)
```

The example runs on the hour. During a batch, scheduled operations and random
activity are merged in timestamp order.

## Defaults

The default `rate=60` and `variance=0.25` produce one activity per second on
average, with delays ranging from 0.75 to 1.25 seconds.
