# Command-line interface

The CLI runs the built-in demonstration or a user-defined flow:

```shell
faker-events run [OPTIONS] [SCRIPT]
```

Display help and the installed version:

```shell
faker-events --help
faker-events --version
faker-events run --help
```

## Built-in demonstration

Run the account and payment demonstration:

```shell
faker-events run --profiles 10 --max-events 100 --seed 42
```

Events are written to standard output. Progress and the delivered count are
written to standard error, so stdout can be piped safely.

## Options

| Option | Short | Default | Meaning |
|---|---|---:|---|
| `--profiles` | `-n` | `1` | Number of profiles to generate or load. |
| `--profile-file` | `-p` | none | Load reusable profiles, or create the file when it does not exist. |
| `--update-profiles` | `-u` | false | Save profile mutations after the run. Requires `--profile-file`. |
| `--seed` | | none | Seed profile generation, event selection, timing, and the built-in demo. |
| `--max-events` | `-m` | none | Maximum processing attempts, including skipped attempts. |
| `--start` | | none | ISO 8601 batch start. Requires `--end`. |
| `--end` | | none | ISO 8601 batch end. Requires `--start`. |
| `--pretty` | | false | Write indented console JSON instead of JSON Lines. |

Profile counts and `max-events` must be greater than zero.

## Live runs

Without `--start` and `--end`, the CLI runs live and sleeps between activity
events:

```shell
faker-events run flow.py \
  --profiles 100 \
  --max-events 10_000
```

Press Ctrl+C to stop an unbounded live stream. The CLI exits with status 130
after reporting that the stream stopped.

## Virtual-time batches

Provide both boundaries to run without sleeping:

```shell
faker-events run flow.py \
  --profiles 100 \
  --start 2026-01-01T00:00:00+00:00 \
  --end 2026-01-08T00:00:00+00:00
```

Use timezone-aware ISO 8601 values when possible. Naive values are interpreted
as UTC by the event generator.

## User flow scripts

A script must expose a callable named `build`. The CLI calls it with profiles,
the console output, and runtime options:

```python
from faker_events import (
    Event,
    EventGenerator,
    GeneratorConfig,
    Output,
    Profile,
)


def build(
    profiles: list[Profile],
    output: Output,
    *,
    seed: int | None = None,
    max_events: int | None = None,
) -> EventGenerator:
    def identify(context, profile):
        return {
            "event_id": context.id,
            "event_time": context.time.isoformat(),
            "user_id": profile.id,
        }

    event = Event(
        {"type": "user.active"},
        identify,
        limit=0,
        rate=12,
    )
    return EventGenerator(
        profiles,
        event,
        output=output,
        config=GeneratorConfig(
            seed=seed,
            max_events=max_events,
        ),
    )
```

Run it:

```shell
faker-events run flow.py --profiles 10 --max-events 100
```

The builder must return an `EventGenerator`. Accepting `**options` is also
valid:

```python
def build(profiles, output, **options):
    ...
```

Use the supplied output to preserve CLI JSON and `--pretty` behavior. Library
code is usually a better fit when the application needs Kafka, Kinesis, or a
custom output.

## Reusable profiles

Create a profile file on the first run and load it on later runs:

```shell
faker-events run flow.py \
  --profiles 100 \
  --profile-file profiles.json
```

The file is created immediately when it does not exist. Existing files are
validated before the flow starts.

Add `--update-profiles` when event transforms modify profile fields that
should be written back:

```shell
faker-events run flow.py \
  --profiles 100 \
  --profile-file profiles.json \
  --update-profiles
```

State stored in `State` is not written to the profile file. Put durable values
on the profile itself.

## Output formatting

Compact JSON Lines is the default:

```json
{"type":"user.active","user_id":"1000"}
```

`--pretty` emits indented JSON for people to read. Because one event may span
multiple lines, do not use it for consumers expecting JSON Lines.

## Common errors

| Error | Resolution |
|---|---|
| Script does not expose `build` | Define a callable `build(profiles, output, **options)`. |
| Builder returns the wrong type | Return an `EventGenerator` instance. |
| Only one batch boundary supplied | Supply both `--start` and `--end`. |
| `--update-profiles` used alone | Add `--profile-file`. |
| Profile file contains too few entries | Request fewer profiles or regenerate the file. |
| Invalid profile JSON | Correct the JSON and required profile fields. |
| Stream never stops | Add finite event limits or `--max-events`. |
| No output from conditional events | Check whether transforms return `SKIP`. |

Exceptions raised while importing a flow script or constructing its generator
are reported directly rather than being masked as generic import errors.
