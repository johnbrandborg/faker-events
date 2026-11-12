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
        fake: Faker | None = None,
        *,
        locale: str | list[str] = "en_US",
        seed: int | None = None,
        faker: Faker | None = None,
    ) -> None:
        if fake is not None and faker is not None:
            raise ValueError("provide either fake or faker, not both")
        self.faker = faker or fake or Faker(locale)
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
        gender = fake.random_element(("female", "male"))
        if gender == "female":
            first_name = fake.first_name_female()
            middle_name = fake.first_name_female()
            prefix_name = fake.prefix_female()
            suffix_name = fake.suffix_female()
        else:
            first_name = fake.first_name_male()
            middle_name = fake.first_name_male()
            prefix_name = fake.prefix_male()
            suffix_name = fake.suffix_male()
        last_name = fake.last_name()
        address1 = self._create_address()
        address2 = self._create_address()
        phone1 = fake.phone_number()
        phone2 = fake.phone_number()

        return Profile(
            id=str(index + 1000),
            uuid=str(fake.uuid4()),
            username=simple["username"],
            name=f"{first_name} {last_name}",
            gender=gender,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            prefix_name=prefix_name,
            suffix_name=suffix_name,
            birthdate=fake.date_of_birth(minimum_age=18, maximum_age=80),
            blood_group=(
                f"{fake.random_element(('A', 'B', 'AB', 'O'))}{fake.random_element(('+', '-'))}"
            ),
            email=f"{first_name}.{last_name}@{fake.domain_name()}",
            employer=fake.company(),
            job=fake.job(),
            address=address1["full_address"],
            city=address1["city"],
            state=address1["state"],
            postcode=address1["postcode"],
            phone=phone1,
            full_address1=address1["full_address"],
            building_number1=address1["building_number"],
            street_name1=address1["street_name"],
            street_suffix1=address1["street_suffix"],
            state1=address1["state"],
            postcode1=address1["postcode"],
            city1=address1["city"],
            phone1=phone1,
            full_address2=address2["full_address"],
            building_number2=address2["building_number"],
            street_name2=address2["street_name"],
            street_suffix2=address2["street_suffix"],
            state2=address2["state"],
            postcode2=address2["postcode"],
            city2=address2["city"],
            phone2=phone2,
            driver_license=fake.bothify("?#####"),
            license_plate=fake.license_plate(),
        )

    def _create_address(self) -> dict[str, str]:
        fake = self.faker
        building_number = fake.building_number()
        full_street_name = fake.street_name()
        street_parts = full_street_name.rsplit(" ", 1)
        street_name = street_parts[0]
        street_suffix = street_parts[1] if len(street_parts) == 2 else ""
        state = fake.state_abbr()
        postcode = fake.postcode()
        city = fake.city()
        return {
            "full_address": (f"{building_number} {full_street_name}, {city}, {state} {postcode}"),
            "building_number": building_number,
            "street_name": street_name,
            "street_suffix": street_suffix,
            "state": state,
            "postcode": postcode,
            "city": city,
        }
