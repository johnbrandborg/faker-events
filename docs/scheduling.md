# Scheduled operations

Scheduled events model work performed by a system at known times, such as
charging fees, expiring sessions, applying interest, or taking snapshots.

```python
from faker_events import Event

hourly_fee = Event(
    {"type": "account.fee"},
    charge_fee,
    state=account,
    schedule="0 * * * *",
    limit=0,
)
```

Schedules use cron syntax supported by `croniter`. Invalid expressions are
rejected when the event is created.

## Activity versus scheduled work

Activity timing uses `rate` and `variance`. Scheduled operations use
`schedule`:

```python
activity = Event(
    {"type": "money.saved"},
    save_money,
    rate=12,
    variance=0.25,
)
scheduled = Event(
    {"type": "interest.applied"},
    apply_interest,
    schedule="0 0 * * *",
)
```

`rate`, `variance`, grouping, and event chaining do not control scheduled
occurrences. A scheduled event runs only on its cron ticks.

## Per-profile execution

At each cron tick, the operation runs once for every profile:

```python
def snapshot(context, profile):
    return {
        "type": "account.snapshot",
        "user_id": profile.id,
        "balance": context.state["balance"],
    }
```

A schedule with `limit=2` and ten profiles can therefore process twenty event
attempts.

The schedule limit counts cron ticks, not delivered events:

- `limit=1` runs one tick for every profile;
- `limit=2` runs two ticks for every profile;
- `limit=0` continues indefinitely in live mode.

Returning `SKIP` suppresses one profile's output, but the tick still counts
toward the schedule limit.

## Conditional operations

Scheduled operations can inspect current state and do nothing when their
condition is not met:

```python
from faker_events import SKIP


def charge_fee(context, _profile):
    if context.state["balance"] < 10:
        return SKIP

    context.state["balance"] -= 10
    return {
        "change": -10,
        "balance": context.state["balance"],
    }
```

Reuse the same `State` object on activity and scheduled events so they operate
on the same per-profile data.

## Batch scheduling

A virtual-time batch merges random activity and scheduled operations in
timestamp order:

```python
generator.batch(
    datetime(2026, 1, 1, tzinfo=UTC),
    datetime(2026, 1, 2, tzinfo=UTC),
)
```

The first scheduled occurrence is the first cron time strictly after the
batch start. An occurrence exactly at the batch end is included.

Batch execution does not sleep. It calculates timestamps and processes the
entire range as quickly as the transforms and output allow.

Do not rely on a particular order for unrelated activity and scheduled work
that receive exactly the same timestamp. Express required ordering as state
conditions or an activity sequence.

## Live scheduling

`run_live()` calculates the next cron occurrence from the current time and
waits until that time. Every scheduled definition runs in its own async task,
while activity runs concurrently.

A live generator with only unlimited schedules runs until it is cancelled.
Use finite schedule limits or cancel the surrounding task when a bounded run
is required.

## Timezones

Schedules use `GeneratorConfig.timezone`, which defaults to UTC:

```python
from faker_events import GeneratorConfig

config = GeneratorConfig(timezone="Europe/Copenhagen")
generator = EventGenerator(profiles, events, config=config)
```

Use an IANA timezone name so daylight-saving transitions are handled by the
standard timezone database.

Aware batch datetimes are converted to the configured timezone. Naive batch
datetimes are interpreted as UTC and then converted. Prefer aware datetimes to
make the intended instant explicit.

## State lifetime

Scheduled state survives for the full continuous run, including multi-day
live and batch runs. Starting another batch or live run resets `State`.

See [State lifecycle and persistence](state-lifecycle.md) when a scheduled
operation must retain data across separate runs.
