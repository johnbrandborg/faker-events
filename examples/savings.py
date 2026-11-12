"""Stateful savings activity with a scheduled account fee.

Run a two-minute virtual-time simulation:

    faker-events run examples/savings.py --profiles 1 \
      --start 2026-01-01T00:00:00+00:00 \
      --end 2026-01-01T00:02:00+00:00
"""

from faker_events import (
    SKIP,
    Event,
    EventContext,
    EventGenerator,
    GeneratorConfig,
    Output,
    Profile,
    State,
)


def build(
    profiles: list[Profile],
    output: Output,
    *,
    seed: int | None = None,
    max_events: int | None = None,
) -> EventGenerator:
    account = State(
        {
            "type": "",
            "change": 0,
            "total": 0,
        }
    )

    def save(amount: int):
        def transform(context: EventContext, _profile: Profile) -> dict[str, int | str]:
            context.data["total"] += amount
            return {
                "type": "money.saved",
                "change": amount,
                "total": context.data["total"],
            }

        return transform

    def hourly_fee(
        context: EventContext,
        _profile: Profile,
    ):
        if context.data["total"] < 10:
            return SKIP
        context.data["total"] -= 10
        return {
            "type": "account.fee",
            "change": -10,
            "total": context.data["total"],
        }

    saved_ten = Event(account, save(10), grouped=True)
    saved_more = Event(account, save(110))
    saved_ten >> saved_more

    fee = Event(
        account,
        hourly_fee,
        schedule="* * * * *",
        limit=2,
    )

    return EventGenerator(
        profiles,
        [saved_ten, fee],
        output=output,
        config=GeneratorConfig(seed=seed, max_events=max_events),
    )
