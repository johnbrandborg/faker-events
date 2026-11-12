# Profiles

Profiles represent the people or entities that events act on. Each event
transform receives the selected profile:

```python
def signed_in(context, profile):
    return {
        "event_id": context.id,
        "user_id": profile.id,
        "name": profile.name,
    }
```

## Profile model

The required field is `id`. `name` defaults to an empty string and
`birthdate` is optional:

```python
from faker_events import Profile

profile = Profile(
    id="customer-1000",
    name="Ada Lovelace",
    plan="premium",
)
```

Profiles allow additional fields. Those fields remain available through
attribute access and are included when the profile is saved:

```python
profile.last_event = "user.signed_in"
profile.total_orders = 4
```

Assignment to declared fields is validated. For example, `birthdate` is a
`date` in Python and is serialized as an ISO date in JSON.

Use `profile.as_dict()` or `profile.model_dump()` when a dictionary is needed.

## Generating profiles

`ProfileGenerator` creates realistic person records:

```python
from faker_events import ProfileGenerator

profile_generator = ProfileGenerator(locale="en_GB", seed=42)
profiles = profile_generator.create(100)
```

Generated profiles include:

- identifiers: `id`, `uuid`, and `username`;
- identity: `name`, gender, first, middle, last, prefix, and suffix names;
- personal data: birthdate, blood group, email, employer, and job;
- simple aliases: address, city, state, postcode, and phone;
- two complete address and phone sets using fields ending in `1` and `2`;
- driver license and license plate.

Generated IDs begin at `"1000"` for each new `create()` call.

## Deterministic generation

Pass a seed to reproduce generated profiles with the same Faker and
faker-events versions:

```python
first = ProfileGenerator(seed=42).create(10)
second = ProfileGenerator(seed=42).create(10)

assert first == second
```

The event generator has a separate seed for event selection and timing. The
CLI's `--seed` option supplies both.

## Locales and custom Faker instances

Pass one locale or a list of locales:

```python
profiles = ProfileGenerator(locale="da_DK", seed=42).create(10)
profiles = ProfileGenerator(locale=["en_GB", "fr_FR"], seed=42).create(10)
```

An existing Faker instance can be supplied positionally or with `faker=`:

```python
from faker import Faker

fake = Faker("en_AU")
profile_generator = ProfileGenerator(fake)
```

Do not pass both the positional `fake` argument and `faker=`.

## Saving and loading

Save the generator's current entries as readable JSON:

```python
profile_generator.save("profiles.json")
```

Load and validate a profile file:

```python
profiles = ProfileGenerator().load("profiles.json")
```

Limit the number loaded:

```python
profiles = ProfileGenerator().load("profiles.json", limit=100)
```

`load_or_create()` loads an existing file or creates and saves a new one:

```python
profile_generator = ProfileGenerator(seed=42)
profiles = profile_generator.load_or_create(100, "profiles.json")
```

If an existing file contains fewer profiles than requested,
`load_or_create()` raises an error instead of silently running with fewer
entities.

## Persisting event mutations

Event transforms receive mutable profile objects:

```python
def renew_subscription(_context, profile):
    profile.plan = "premium"
    profile.renewal_count = getattr(profile, "renewal_count", 0) + 1
```

For CLI runs, use `--update-profiles` with `--profile-file`:

```shell
faker-events run subscriptions.py \
  --profiles 100 \
  --profile-file profiles.json \
  --update-profiles
```

For library use, load and save through the same generator:

```python
profile_generator = ProfileGenerator()
profiles = profile_generator.load("profiles.json")

EventGenerator(profiles, events).batch(start, end)

profile_generator.save("profiles.json")
```

Existing custom fields and new mutations are retained.

## Profile state versus Event State

Profile fields can survive separate generators and processes when saved.
`State` is reset for each generator run.

Use profiles for durable session IDs, cumulative counters, and entity
attributes. Use `State` for scenario data shared by events during one
continuous run.

See [State lifecycle and persistence](state-lifecycle.md) for examples and
reset boundaries.
