# Stateful activity and scheduled operations

Faker Events models two sources of change:

- **Activity events** represent things people or external actors do, such as
  saving money, buying a product, signing in, or changing an address.
- **Scheduled operations** represent work performed by the system, such as
  charging fees, applying interest, expiring sessions, settling transactions,
  or producing snapshots.

Both can inspect and mutate the same state for an entity.

## Shared state

Create one `State` definition and reuse it across related events:

```python
from faker_events import Event, State

account = State({"total": 0})

saved = Event(
    {"type": "money.saved"},
    save_money,
    state=account,
)
fee = Event(
    {"type": "account.fee"},
    charge_fee,
    state=account,
    schedule="0 * * * *",
)
```

The generator creates a deep copy of the initial state for every profile.
Profiles therefore evolve independently, and separate generators do not leak
state into one another.

Transforms access shared state through `context.state`:

```python
def save_money(context, _profile):
    context.state["total"] += 110
    return {
        "change": 110,
        "total": context.state["total"],
    }
```

The returned mapping updates the event output. It does not replace the shared
state.

## Shared state as the event structure

For flows where every event represents a snapshot of the same entity, pass
`State` directly as the event template:

```python
account = State(
    {
        "type": "",
        "change": 0,
        "total": 0,
    }
)

saved = Event(account, save_money)
fee = Event(account, charge_fee, schedule="0 * * * *")
```

In this form, `context.data` and `context.state` refer to the same per-profile
state. This provides the concise stateful behavior familiar from Faker Events
1.x without its global template-hash store.

## Conditional scheduled operations

Return `SKIP` when a system operation has no work to perform:

```python
from faker_events import SKIP


def charge_fee(context, _profile):
    if context.state["total"] < 10:
        return SKIP

    context.state["total"] -= 10
    return {
        "change": -10,
        "total": context.state["total"],
    }
```

A skipped attempt:

- emits no event;
- still consumes its event or schedule limit;
- still advances time and the flow;
- preserves state and profile mutations made before `SKIP`.

`max_events` counts processing attempts, including skipped attempts. This
ensures that an infinite conditional flow can be bounded.

## Schedule behavior

At each matching cron time, a scheduled event runs once for every profile.
Its `limit` counts cron ticks:

- `limit=1` runs one tick for every profile;
- `limit=2` runs two ticks for every profile;
- `limit=0` continues indefinitely in live mode.

Activity and scheduled operations are processed in timestamp order during a
virtual-time batch. Future activity cannot affect a scheduled operation in the
past.

## Complete savings example

The runnable [`examples/savings.py`](../examples/savings.py) flow:

1. saves $10, producing a total of $10;
2. saves $110, producing a total of $120;
3. charges a scheduled $10 fee, producing a total of $110;
4. charges the next fee, producing a total of $100.

Run it without waiting:

```shell
faker-events run examples/savings.py --profiles 1 \
  --start 2026-01-01T00:00:00+00:00 \
  --end 2026-01-01T00:02:00+00:00
```

Output:

```json
{"type":"money.saved","change":10,"total":10}
{"type":"money.saved","change":110,"total":120}
{"type":"account.fee","change":-10,"total":110}
{"type":"account.fee","change":-10,"total":100}
```

Generated output may include additional fields when they are declared in the
shared state.

## Live and async execution

Use the synchronous interface in ordinary scripts:

```python
generator.start()
generator.batch(start, end)
```

Use the async interface when integrating with an existing event loop:

```python
await generator.run_live()
await generator.run_batch(start, end)
```
