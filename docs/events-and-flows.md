# Events and flows

An `Event` defines an event structure, an optional transform, its number of
occurrences, and its timing.

```python
from faker_events import Event

signed_in = Event(
    {"type": "user.signed_in"},
    enrich_sign_in,
    limit=3,
    rate=12,
    variance=0.10,
    name="sign-in",
)
```

## Event options

| Option | Default | Meaning |
|---|---:|---|
| `template` | required | String-keyed mapping used as the event's initial data, or a `State` used as both data and shared state. |
| `transform` | `None` | Callable receiving `(context, profile)` before delivery. |
| `limit` | `1` | Occurrences per profile. `0` repeats indefinitely. |
| `state` | `None` | Explicit `State` shared with other events for the same profile. |
| `rate` | `60` | Activity pace in events per minute. |
| `variance` | `0.25` | Random timing variance from `0` to `1`. |
| `grouped` | `False` | Remove the delay and group a successor at the same time. |
| `schedule` | `None` | A cron expression for a scheduled operation. |
| `name` | template `type` or `"event"` | Diagnostic name used in representations and errors. |

Event templates and initial state are deep-copied before use. Template keys
must be strings. Negative limits, nonpositive rates, invalid variance, and
invalid cron expressions are rejected when the event is constructed.

See [Event timing](event-timing.md) for rate and variance calculations.

## Transforms

A transform receives an `EventContext` and the selected `Profile`:

```python
def enrich_sign_in(context, profile):
    return {
        "event_id": context.id,
        "event_time": context.time.isoformat(),
        "user_id": profile.id,
    }
```

`EventContext` exposes:

| Attribute | Meaning |
|---|---|
| `data` | Mutable data for the current event and profile. |
| `state` | Explicit shared state, or `data` when no separate state was supplied. |
| `id` | Generator-local integer processing ID. |
| `profile_index` | Index of the selected profile in the generator. |
| `time` | Timezone-aware event `datetime`. |

A transform may:

- mutate `context.data` or `context.state` and return `None`;
- return a mapping, which is deeply merged into `context.data`;
- return `SKIP` to suppress delivery.

```python
from faker_events import SKIP


def require_balance(context, _profile):
    if context.state["balance"] == 0:
        return SKIP
    return {"balance": context.state["balance"]}
```

Mutations made before `SKIP` remain in state and on the profile. A skipped
attempt consumes the event occurrence and counts toward `max_events`.

Transforms must not return arbitrary values. Return a mapping, `SKIP`, or
`None`.

## Event data and shared state

An ordinary mapping belongs to that event definition. Reusing equal mappings
does not make separate events share data.

Use one explicit `State` when multiple activity or scheduled events must
operate on the same data:

```python
from faker_events import Event, State

account = State({"balance": 0})
deposit = Event({"type": "deposit"}, deposit_money, state=account)
fee = Event({"type": "fee"}, charge_fee, state=account)
```

Pass `State` as the template when every emitted event should be a snapshot of
that shared structure:

```python
account = State({"type": "", "balance": 0})
deposit = Event(account, deposit_money)
fee = Event(account, charge_fee)
```

Generated events are deep-copy snapshots. Later mutations do not alter events
that were already generated or delivered.

See [State lifecycle and persistence](state-lifecycle.md) before deciding
whether data belongs in `State` or on a `Profile`.

## Sequences

Connect events with `then()` or `>>`:

```python
registered = Event({"type": "registered"})
verified = Event({"type": "verified"})
subscribed = Event({"type": "subscribed"}, limit=2)

registered >> verified >> subscribed
```

The next event becomes active for that profile only after the current event's
limit is exhausted.

The v1-compatible `next` property and `<<` operator remain available:

```python
registered.next = verified
registered << verified
```

## Branches and multiple roots

Pass a sequence to start multiple successors:

```python
registered >> [welcome_email, analytics_record]
```

Both successors become active after `registered` completes. Their relative
order is selected by the generator unless grouping forces adjacency.

Pass multiple root events to run independent flows for every profile:

```python
generator = EventGenerator(
    profiles,
    [account_flow, browsing_flow, support_flow],
)
```

## Grouping

Use `&` when a successor must immediately follow its parent:

```python
order_created & inventory_reserved
```

The grouped successor remains adjacent for the same profile and receives the
same timestamp in a virtual-time batch. `grouped=True` directly on an event
also removes its activity delay.

An infinite zero-delay flow can consume CPU continuously. Use a non-grouped
event, a finite `limit`, or `GeneratorConfig(max_events=...)` when appropriate.

## Limits

`limit` applies per profile:

```python
payment = Event({"type": "payment"}, limit=3)
```

With ten profiles, that event can run thirty times. `limit=0` means unlimited.

`GeneratorConfig.max_events` is a generator-wide safety bound on processing
attempts. It includes skipped attempts:

```python
from faker_events import EventGenerator, GeneratorConfig

generator = EventGenerator(
    profiles,
    event,
    config=GeneratorConfig(max_events=10_000),
)
```

## Generator configuration

`GeneratorConfig` validates runtime settings:

| Option | Default | Meaning |
|---|---:|---|
| `seed` | `None` | Seed for event selection and timing variance. |
| `timezone` | `"UTC"` | IANA timezone used by event times and schedules. |
| `max_events` | `None` | Positive generator-wide processing-attempt limit. |

Configuration is frozen after creation. Construct a new configuration when
settings need to change.

## Lazy generation

`generate()` yields `GeneratedEvent` values without opening an output:

```python
for generated in generator.generate(start=start):
    print(generated.time, generated.data)
```

A `GeneratedEvent` contains `data`, `time`, `delay`, and `grouped`. After a
finite flow is exhausted, calling `generate()` again resets it to its initial
state. Call `reset()` explicitly when an immediate reset is required.
