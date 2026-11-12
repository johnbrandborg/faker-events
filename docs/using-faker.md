# Generate realistic data with Faker

[Faker](https://faker.readthedocs.io/en/stable/) is the core data-generation
library used by Faker Events and the project that inspired it. Faker Events
extends the idea of convenient fake-data generation to stateful event streams.
Faker provides names, addresses, companies, dates, identifiers, text, and many
other realistic values so that event fields do not need to be hand-written.

The two libraries have different responsibilities:

| Library | Responsibility |
|---|---|
| Faker | Generate realistic field values. |
| Faker Events | Model profiles, state changes, event timing, flows, and delivery. |

`faker-events` installs Faker as a dependency, so no separate installation is
required.

## Start with generated profiles

`ProfileGenerator` uses Faker to create people with identity, contact,
employment, and address fields:

```python
from faker_events import ProfileGenerator

profiles = ProfileGenerator(locale="en_US", seed=42).create(100)

print(profiles[0].name)
print(profiles[0].email)
print(profiles[0].employer)
```

Use this when the built-in profile fields fit the scenario. See
[Profiles](profiles.md) for the complete field list, locales, and persistence.

## Generate event fields

Create a Faker instance and call its providers from an event transform:

```python
from faker import Faker
from faker_events import Event

fake = Faker("en_US")
fake.seed_instance(42)


def create_order(context, profile):
    return {
        "event_id": context.id,
        "event_time": context.time.isoformat(),
        "type": "order.created",
        "customer_id": profile.id,
        "order_id": fake.uuid4(),
        "product": fake.catch_phrase(),
        "amount": float(
            fake.pydecimal(
                left_digits=3,
                right_digits=2,
                positive=True,
            )
        ),
        "shipping_address": fake.address(),
    }


order_created = Event(
    {"type": "order.created"},
    create_order,
    limit=3,
    rate=6,
    variance=0.2,
)
```

Faker offers
[standard providers](https://faker.readthedocs.io/en/stable/providers.html)
for common domains. Useful methods include:

- `name()`, `email()`, `phone_number()`, and `address()`;
- `company()`, `job()`, and `catch_phrase()`;
- `date_time_between()`, `date_of_birth()`, and `future_date()`;
- `uuid4()`, `bothify()`, and `random_int()`;
- `sentence()`, `paragraph()`, and `random_element()`.

## Seed both generators

Faker and Faker Events use separate random-number generators. Seed both when
the same inputs must produce the same values, event selection, and timing:

```python
from faker import Faker
from faker_events import EventGenerator, GeneratorConfig, ProfileGenerator

fake = Faker("en_GB")
fake.seed_instance(42)

profiles = ProfileGenerator(locale="en_GB", seed=42).create(100)
generator = EventGenerator(
    profiles,
    order_created,
    config=GeneratorConfig(seed=42, max_events=300),
)
```

The CLI's `--seed` option seeds its built-in profile and event generators. A
Faker instance created inside a user script must still be seeded by that
script.

Reproducibility also depends on using the same Faker and faker-events versions
because provider datasets can change between releases.

## Use locales

Pass a locale to generate region-appropriate names, addresses, phone numbers,
and identifiers:

```python
fake = Faker("da_DK")
profiles = ProfileGenerator(locale="da_DK", seed=42).create(100)
```

Faker can mix multiple locales:

```python
fake = Faker(["en_GB", "fr_FR", "de_DE"])
```

Not every provider exists for every locale. Faker selects a locale that
supports the requested provider where possible.

Multi-locale Faker instances need extra care when they are seeded. Calling
`seed_instance()` gives every internal locale generator the same seed. Methods
that do not depend on locale data, including `uuid4()`, can then produce the
same sequence in each locale. Use a single-locale Faker for identifiers, or
seed each locale differently:

```python
fake = Faker(["en_GB", "fr_FR", "de_DE"])

for index, locale in enumerate(fake.locales):
    fake.seed_locale(locale, 42 + index)
```

Use `seed_locale()` rather than relying on the order of `fake.factories`.

## Add domain-specific providers

For repeated domain values, define a custom Faker provider instead of
scattering lists and formatting rules across transforms:

```python
from collections import OrderedDict

from faker import Faker
from faker.providers import BaseProvider


class CommerceProvider(BaseProvider):
    def subscription_plan(self):
        plans = OrderedDict(
            (
                ("free", 0.70),
                ("pro", 0.25),
                ("enterprise", 0.05),
            )
        )
        return self.random_elements(
            plans,
            length=1,
            use_weighting=True,
        )[0]

    def account_id(self):
        return self.bothify("ACCT-########")


fake = Faker()
fake.add_provider(CommerceProvider)

plan = fake.subscription_plan()
account_id = fake.account_id()
```

Custom providers keep event schemas readable and can be reused across flows.
Faker normally enables weighting, but passing `use_weighting=True` explicitly
keeps a provider's weighted choice correct even when its Faker instance was
created with `use_weighting=False`.

`add_provider()` is not available on a multi-locale Faker proxy. Add the
provider to each internal generator instead:

```python
fake = Faker(["en_GB", "fr_FR", "de_DE"])

for locale in fake.locales:
    fake[locale].add_provider(CommerceProvider)
```

## Generate coherent locations

Use Faker's
[`local_latlng()`](https://faker.readthedocs.io/en/stable/providers/faker.providers.geo.html)
when a city, country, latitude, and longitude must describe the same place.
Generate them together rather than selecting each field independently.

The available place data varies by country and can be sparse for some locales.
Inspect the distribution before relying on it for a large or geographically
varied dataset.

## Keep generated data coherent

Realistic values alone do not make a realistic scenario. Use Faker for field
values, then use profiles and `State` to preserve business relationships:

- keep stable customer attributes on the profile;
- store run-scoped balances, statuses, and counters in `State`;
- derive related event fields from the same state instead of generating each
  independently;
- use weighted choices when categories should not be uniformly distributed;
- keep foreign keys from existing profiles or entities.

For example, an `order.shipped` event should reuse the order ID and shipping
address created by `order.created`, not ask Faker to create new values.

## Faker or an LLM?

Prefer Faker for structured values that can be generated locally. It is fast,
repeatable, inexpensive, and available without a network call. Use an LLM
only when the scenario needs richer domain-specific text that Faker providers
cannot supply, such as a detailed support conversation or incident report.

When asking an LLM to design a Faker Events simulation, state this requirement
explicitly:

```text
Use the Faker Python package for names, addresses, companies, identifiers,
dates, and other structured fake values. Seed Faker separately from the
Faker Events generator. Do not hand-roll values that a Faker provider
already supplies.
```

See [AI-assisted generation and analysis](ai-workflows.md) for a complete
workflow.
