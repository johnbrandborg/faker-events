from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratorConfig(BaseModel):
    """Validated runtime settings kept outside the event hot path."""

    model_config = ConfigDict(frozen=True)

    seed: int | None = None
    timezone: str = "UTC"
    max_events: int | None = Field(
        default=None,
        gt=0,
        description="Maximum processing attempts, including skipped events.",
    )


class Profile(BaseModel):
    """A mutable entity whose state can evolve across an event flow."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    id: str
    name: str = ""
    birthdate: date | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


class State:
    """Definition for mutable state shared by events for each profile.

    A generator creates an isolated copy of ``initial`` for every profile.
    Reusing one State instance across activity and scheduled events lets both
    operate on the same entity state without global data.
    """

    __slots__ = ("initial",)

    def __init__(self, initial: Mapping[str, Any] | None = None, /, **values: Any) -> None:
        combined = dict(initial or {})
        combined.update(values)
        if not all(isinstance(key, str) for key in combined):
            raise TypeError("state keys must be strings")
        self.initial = deepcopy(combined)

    def __repr__(self) -> str:
        return f"State({self.initial!r})"


class EventContext:
    """Mutable event state passed to an event transform."""

    __slots__ = ("data", "id", "profile_index", "state", "time")

    def __init__(
        self,
        *,
        data: dict[str, Any],
        state: dict[str, Any] | None = None,
        event_id: int,
        profile_index: int,
        time: datetime,
    ) -> None:
        self.data = data
        self.state = state if state is not None else data
        self.id = event_id
        self.profile_index = profile_index
        self.time = time

    def update(self, values: Mapping[str, Any]) -> None:
        _deep_merge(self.data, values)


class GeneratedEvent(BaseModel):
    """An event plus delivery metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    data: dict[str, Any]
    time: datetime
    delay: float = Field(ge=0)
    grouped: bool = False

    @field_validator("data")
    @classmethod
    def data_must_be_a_string_keyed_mapping(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not all(isinstance(key, str) for key in value):
            raise ValueError("event keys must be strings")
        return value


def _deep_merge(target: dict[str, Any], values: Mapping[str, Any]) -> None:
    for key, value in values.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            _deep_merge(current, value)
        else:
            target[key] = value
