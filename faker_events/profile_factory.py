from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson
from faker import Faker
from pydantic import TypeAdapter

from .models import Profile

_PROFILE_LIST = TypeAdapter(list[Profile])


class ProfileGenerator:
    """Create deterministic, validated entities for event flows."""

    def __init__(
        self,
        *,
        locale: str | list[str] = "en_US",
        seed: int | None = None,
        faker: Faker | None = None,
    ) -> None:
        self.faker = faker or Faker(locale)
        if seed is not None:
            self.faker.seed_instance(seed)
        self.entries: list[Profile] = []

    def create(self, count: int) -> list[Profile]:
        if count < 1:
            raise ValueError("count must be greater than zero")

        self.entries = [self._create_profile(index) for index in range(count)]
        return self.entries

    def load(self, path: str | Path, *, limit: int | None = None) -> list[Profile]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than zero")
        payload = orjson.loads(Path(path).read_bytes())
        profiles = _PROFILE_LIST.validate_python(payload)
        self.entries = profiles[:limit]
        return self.entries

    def load_or_create(
        self,
        count: int,
        path: str | Path | None = None,
    ) -> list[Profile]:
        if path is None:
            return self.create(count)
        profile_path = Path(path)
        if profile_path.exists():
            profiles = self.load(profile_path, limit=count)
            if len(profiles) < count:
                raise ValueError(
                    f"{profile_path} contains {len(profiles)} profiles; {count} requested"
                )
            return profiles
        profiles = self.create(count)
        self.save(profile_path)
        return profiles

    def save(self, path: str | Path) -> None:
        profile_path = Path(path)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        data = [profile.model_dump(mode="json") for profile in self.entries]
        profile_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2) + b"\n")

    def _create_profile(self, index: int) -> Profile:
        fake = self.faker
        simple: dict[str, Any] = fake.simple_profile()
        address = fake.street_address()
        return Profile(
            id=str(index + 1000),
            uuid=str(fake.uuid4()),
            username=simple["username"],
            name=simple["name"],
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            birthdate=simple["birthdate"],
            email=simple["mail"],
            employer=fake.company(),
            job=fake.job(),
            address=address,
            city=fake.city(),
            state=fake.state_abbr(),
            postcode=fake.postcode(),
            phone=fake.phone_number(),
            driver_license=fake.bothify("?#####"),
            license_plate=fake.license_plate(),
        )
