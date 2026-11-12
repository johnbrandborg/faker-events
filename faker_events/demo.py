from __future__ import annotations

from typing import Any

from faker import Faker

from .engine import Event, EventGenerator
from .models import EventContext, GeneratorConfig, Profile, State
from .outputs import Output


def build(
    profiles: list[Profile],
    output: Output,
    *,
    seed: int | None = None,
    max_events: int | None = None,
) -> EventGenerator:
    fake = Faker()
    if seed is not None:
        fake.seed_instance(seed)

    account = State(
        {
            "type": "account.opened",
            "event_id": 0,
            "event_time": "",
            "user_id": "",
            "name": "",
            "balance": 0,
        }
    )

    def open_account(context: EventContext, profile: Profile) -> dict[str, Any]:
        return {
            "event_id": context.id,
            "event_time": context.time.isoformat(),
            "user_id": profile.id,
            "name": profile.name,
        }

    def payment(context: EventContext, _profile: Profile) -> dict[str, Any]:
        context.state["balance"] += fake.random_int(5, 250)
        return {
            "type": "payment.received",
            "event_id": context.id,
            "event_time": context.time.isoformat(),
            "balance": context.state["balance"],
        }

    opened = Event(account, open_account, name="account.opened")
    paid = Event(
        account,
        payment,
        limit=3,
        rate=120,
        name="payment.received",
    )
    opened >> paid

    return EventGenerator(
        profiles,
        opened,
        output=output,
        config=GeneratorConfig(seed=seed, max_events=max_events),
    )
