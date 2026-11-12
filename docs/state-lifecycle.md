# State lifecycle and persistence

Faker Events has two places for mutable entity data:

- `State` holds data for one profile during one generator run.
- `Profile` holds entity data that can outlive a generator run.

Choosing the correct lifetime prevents accidental resets and accidental state
sharing.

## Generator-scoped State

One `State` definition can be shared by related events:

```python
from faker_events import Event, State

account = State({"balance": 0})
deposit = Event({"type": "deposit"}, deposit_money, state=account)
fee = Event(
    {"type": "fee"},
    charge_fee,
    state=account,
    schedule="0 * * * *",
)
```

The generator creates an isolated deep copy for each profile. During one
continuous run, that copy is shared by every event using the same `State`
definition.

State persists across:

- all activity events in the run;
- scheduled operations in the run;
- skipped event attempts;
- multiple days in one continuous live run;
- a multi-day range in one batch run.

It does not leak between profiles or separate generators.

## Reset boundaries

State returns to its initial value when:

- a new `EventGenerator` is created;
- `generator.reset()` is called;
- `run_live()` starts;
- `run_batch()` or `iter_batch()` starts;
- an exhausted finite `generate()` flow is started again.

One multi-day batch preserves state:

```python
generator.batch(
    datetime(2026, 1, 1, tzinfo=UTC),
    datetime(2026, 1, 8, tzinfo=UTC),
)
```

Seven separate daily `batch()` calls are seven separate runs and each starts
from the initial `State`.

## Durable profile data

Put data on the profile when it must survive a generator reset, a new
generator, or a later process:

```python
from uuid import uuid4


def track_session(context, profile):
    if getattr(profile, "session_id", None) is None:
        profile.session_id = str(uuid4())
        profile.session_event_count = 0

    profile.session_event_count += 1
    return {
        "session_id": profile.session_id,
        "session_event_count": profile.session_event_count,
        "event_id": context.id,
    }
```

Profiles accept additional fields, so an application can attach domain state
such as session IDs, counters, subscription status, or a last-processed
timestamp. Declared profile fields are validated; applications define the
meaning and types of additional fields.

Reusing the same `Profile` objects preserves those mutations across generator
instances in one process:

```python
profiles = ProfileGenerator(seed=42).create(10)

first_day = build_generator(profiles)
first_day.batch(day_one_start, day_one_end)

second_day = build_generator(profiles)
second_day.batch(day_two_start, day_two_end)
```

## Persistence across processes

Use a profile file and `--update-profiles` to save mutations after a CLI run:

```shell
faker-events run sessions.py \
  --profiles 100 \
  --profile-file profiles.json \
  --update-profiles
```

The next invocation loads the updated profile fields:

```shell
faker-events run sessions.py \
  --profiles 100 \
  --profile-file profiles.json \
  --update-profiles
```

Without `--update-profiles`, an existing profile file is loaded but mutations
made during the run are not written back.

Library applications can save explicitly:

```python
profile_generator = ProfileGenerator()
profiles = profile_generator.load("profiles.json")

generator = build_generator(profiles)
generator.batch(start, end)

profile_generator.save("profiles.json")
```

`ProfileGenerator.save()` writes the objects currently held in
`profile_generator.entries`. If profiles are assembled separately, assign
them to `entries` before saving.

## Choosing between State and Profile

Use `State` for:

- account balances evolving within one simulation run;
- activity shared with scheduled operations;
- temporary workflow status;
- data that should reset for a repeatable run.

Use `Profile` for:

- session identity across daily runs;
- cumulative counters across generators;
- entity attributes changed by events;
- checkpoints that must be saved and reloaded.

An event can use both. For example, a profile can retain a durable account ID
while `State` models a balance that resets for each scenario.

## Isolation

Every profile receives a separate state copy. Nested values are deep-copied,
so mutating one profile's list or dictionary does not affect another profile.
Separate generator instances also receive fresh copies even when they reuse
the same event and `State` definitions.
