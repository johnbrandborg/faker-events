from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratorConfig(BaseModel):
    """Validated runtime settings kept outside the event hot path."""

    model_config = ConfigDict(frozen=True)

    seed: int | None = None
    timezone: str = "UTC"
    max_events: int | None = Field(default=None, gt=0)


class Profile(BaseModel):
    """A mutable entity whose state can evolve across an event flow."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    id: str
    name: str = ""
    birthdate: date | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


class EventContext:
    """Mutable event state passed to an event transform."""

    __slots__ = ("data", "id", "profile_index", "time")

    def __init__(
        self,
        *,
        data: dict[str, Any],
        event_id: int,
        profile_index: int,
        time: datetime,
    ) -> None:
        self.data = data
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
