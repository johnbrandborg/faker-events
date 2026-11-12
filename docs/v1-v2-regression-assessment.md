# Faker Events 1.6.0 to 2.0.1 regression assessment

This assessment compares the public behavior of Faker Events 1.6.0 with the
2.0.1 recovery release. It covers the source, tests, README, example, CLI,
stream handlers, profile generation, packaging, and release workflows.

The goal is behavioral continuity, not line-by-line compatibility. Defects and
unsafe global behavior from 1.x are deliberately not preserved.

Assessment sources:

- the complete `1.6.0` source tree and README;
- all 1.x tests and examples;
- the 2.0.1 source, documentation, examples, and public exports;
- executable parity and regression tests;
- package build and metadata validation.

## Status definitions

- **Preserved** — equivalent user-visible behavior remains available.
- **Restored in 2.0.1** — behavior was missing or weakened in 2.0.0 and has
  regression coverage in 2.0.1.
- **Improved** — the same capability exists with stronger behavior.
- **Intentional breaking change** — removed or redesigned as part of the major
  version, with a documented replacement.
- **Not retained** — nonessential behavior or an implementation detail with no
  direct replacement.

## Executive summary

The most serious 2.0.0 regression was shared event state. In 1.x, activity and
scheduled events built from the same template implicitly shared mutable state
for each profile. Version 2.0.0 keyed data by `Event` instance, which broke
flows where scheduled system operations inspect state produced by human
activity.

Version 2.0.1 restores that capability explicitly with `State`, including a
concise v1-style form:

```python
account = State({"type": "", "total": 0})
saved = Event(account, save_money)
fee = Event(account, charge_fee, schedule="0 * * * *")
```

The explicit definition preserves the useful behavior without restoring the
global MD5 template registry that caused state leakage in 1.x.

The assessment also found and corrected dropped generated-profile fields,
post-run profile persistence, synchronous execution convenience, grouped-event
ordering, batch time ordering, and unbounded skipped flows.

## Feature assessment

| Capability | 1.6.0 | 2.0.1 status | Notes |
|---|---|---|---|
| Static and transformed events | `Event(template, profiler)` | **Preserved** | `transform` is the preferred term; positional callback use remains valid. |
| Direct event-data mutation | Mutate `event.data` | **Preserved** | Mutate `context.data`. |
| Returned event updates | Existing keys only | **Improved** | Returned mappings can add keys and safely deep-merge nested mappings. |
| Conditional delivery | Return `"skip"` | **Improved** | Return the unambiguous `SKIP` sentinel. |
| State mutations before skip | Persisted | **Restored in 2.0.1** | Data, shared state, and profile mutations survive a skipped attempt. |
| Shared state across event definitions | Implicit template hash | **Restored in 2.0.1** | Reuse an explicit `State`; no global hash registry. |
| Per-profile state isolation | Deep copy per profile | **Preserved** | Also isolated between generator instances. |
| Stateful scheduled checks | Shared hashed template | **Restored in 2.0.1** | Scheduled and activity events reuse one `State`. |
| Event limits | Per profile; zero is infinite | **Preserved** | Negative limits are now rejected. |
| Rate and variance | `epm`, percentage variance | **Intentional breaking change** | `rate` and fractional `variance` provide validated values. |
| Event chaining | `next`, `>>`, undocumented `<<` | **Preserved** | `then()`, `next`, `>>`, and `<<` are covered. |
| Branching | Assign a list of next events | **Preserved** | Sequence values remain supported. |
| Multiple first flows | Global `set_first_events()` | **Improved** | Pass multiple events directly to an isolated generator. |
| Grouped events | Intended same-time successor; crashed at runtime | **Improved** | `a & b` keeps the successor adjacent with the same timestamp. |
| Lazy generation | `create_events()` tuples | **Intentional breaking change** | `generate()` yields typed `GeneratedEvent` snapshots. |
| Repeated lazy runs | Rebuilt flow table but retained leaked event state | **Improved** | A completed `generate()` flow can run again from deterministic initial state. |
| Synchronous live execution | `start()` | **Restored in 2.0.1** | `start()` wraps the async engine. |
| Async live execution | Internal only | **Improved** | Public `run_live()` supports async applications. |
| Historical batch | Configure globally, then `start()` | **Improved** | `batch()` and `run_batch()` execute directly without global state. |
| Batch cutoff | Could emit after the finish time | **Improved** | No transform or mutation occurs after `end`. |
| Batch schedules | Not implemented | **Improved** | Activity and schedules are merged in timestamp order. |
| Live cron schedules | Once per profile per tick | **Preserved** | Validated at event creation and timezone-aware. |
| Scheduled limits | Count cron ticks | **Preserved** | Skipped ticks still consume limits. |
| Scheduled chaining/rate/grouping | Ignored in 1.x | **Not retained** | Scheduled operations remain cron-driven. |
| Timezone | Local default; global fixed-hour offset option | **Intentional breaking change** | The default is now UTC. `GeneratorConfig.timezone` accepts an IANA timezone and is generator-local. |
| Event IDs | Template-global strings | **Intentional breaking change** | Generator-local integer IDs avoid global coupling. |
| Event timestamps | ISO strings | **Intentional breaking change** | `EventContext.time` is a timezone-aware `datetime`; outputs choose formatting. |
| Profile birthdate | ISO string | **Intentional breaking change** | `Profile.birthdate` is a validated `date`; JSON persistence remains ISO formatted. |
| Mutable profiles | `SimpleNamespace` | **Preserved** | Validated Pydantic profiles allow extra mutable fields. |
| Generated profile schema | Rich person/address fields | **Restored in 2.0.1** | Coherent adult identity/address data, legacy fields, and simpler aliases are provided. |
| Custom Faker instance | `ProfileGenerator(fake)` | **Preserved** | Positional `fake`, `faker=`, locale, and deterministic seed are supported. |
| Profile JSON load/save | Compact unvalidated JSON | **Improved** | Validated JSON, readable formatting, complete extra-field persistence. |
| Missing profile file | Create and save | **Preserved** | `load_or_create()` performs this explicitly. |
| Short profile file | Warn and continue short | **Intentional breaking change** | Raises instead of silently running with fewer profiles. |
| Save mutations after CLI run | `-u` | **Restored in 2.0.1** | `-u/--update-profiles` requires a profile file and preserves custom fields. |
| Console JSON Lines | Default `Stream` | **Preserved** | `ConsoleOutput` uses faster serialization and explicit flushing. |
| Kafka | `kafka-python`, fire-and-forget | **Improved** | `KafkaOutput` uses `confluent-kafka`, acknowledgements, and flush validation. |
| Kinesis | One `put_record` per event | **Improved** | `KinesisOutput` batches with `PutRecords`. |
| Custom destinations | Intended synchronous `send()` object | **Intentional breaking change** | Implement the async `Output` protocol; blocking calls no longer stall the event loop. |
| In-memory destination | User-defined only | **Improved** | `MemoryOutput` is included. |
| Output snapshots | Live mutable dictionaries | **Improved** | Generated and in-memory output snapshots are deep copies. |
| CLI default example | Account/payment/status flow | **Preserved and improved** | The built-in demo now verifies state continuity across account and payments. |
| CLI user scripts | Import for global side effects | **Intentional breaking change** | Scripts expose an explicit `build(...)` function. |
| CLI batch range | Required Python setup | **Improved** | `--start` and `--end` expose virtual-time batches directly. |
| CLI error handling | Broad import masking | **Improved** | File loading and build-contract errors are reported directly. |
| Global generator configuration | Class attributes and setters | **Intentional breaking change** | All state, output, timezone, and randomness are instance-owned. |
| Deterministic generation | Partial Faker behavior | **Improved** | Generator and profile seeds are explicit. |
| Python support | 3.6–3.10 | **Intentional breaking change** | Supported Python versions are 3.11–3.14. |
| Packaging | `setup.py` / `setup.cfg` | **Improved** | `pyproject.toml`, reproducible CI build, provenance, and trusted publishing. |

## 2.0.0 regressions corrected by 2.0.1

The following have dedicated regression tests:

1. Activity and scheduled events share per-profile state.
2. V1-style state-as-template events preserve direct mutations.
3. Shared state cannot leak between profiles or generator instances.
4. Scheduled operations can conditionally skip based on current activity state.
5. The savings scenario produces `$10 → $120 → $110 → $100`.
6. Future activity cannot mutate state before an earlier scheduled operation.
7. No activity transform runs after a batch end boundary.
8. Grouped successors remain adjacent and retain their parent timestamp.
9. The built-in demo retains account identity across payment events.
10. Profile mutations can be saved after CLI execution.
11. Existing custom profile fields survive an update.
12. Generated profiles retain the established 1.x field set.
13. Infinite skipped flows respect `max_events`.
14. Synchronous `start()` and `batch()` remain available.
15. Existing 2.0 exports and ordinary mapping-based events remain available.
16. The documented savings example executes successfully in the test suite.
17. Chaining, branching, multiple first flows, and repeated lazy runs remain available.
18. Generated identities, ages, addresses, and the complete legacy field set are coherent.
19. Default and configured timezone behavior is explicit and tested.
20. In-memory output snapshots do not retain nested mutable references.

## Deliberately unsupported 1.x behavior

These behaviors are not planned for restoration:

- global class-level events, schedules, output, timezone, and batch clocks;
- implicit state sharing based on MD5 hashes of equal dictionaries;
- negative limits;
- the magic string `"skip"`;
- silently discarding new keys returned by transforms;
- naive local timestamps and inconsistent scheduler timezones;
- one-record-at-a-time Kinesis delivery;
- unacknowledged Kafka sends;
- side-effect-based script registration;
- unconditional ANSI status coloring and the unused `colorize_json()` helper;
- accepting malformed profile files or silently using fewer profiles requested;
- scheduled chaining, rate, or grouping, which did not operate in 1.x.

## Remaining migration requirements

The following are intentional source changes that users must make:

| 1.x | 2.x |
|---|---|
| `Event(..., epm=60, variance=25)` | `Event(..., rate=60, variance=0.25)` |
| `Event(..., cron="0 * * * *")` | `Event(..., schedule="0 * * * *")` |
| `return "skip"` | `return SKIP` |
| `EventGenerator.set_first_events(event)` | `EventGenerator(profiles, event)` |
| `EventGenerator.set_stream(stream)` | Pass `output=` to the generator |
| `EventGenerator.set_timezone(2)` | `GeneratorConfig(timezone="Europe/Copenhagen")` |
| `Stream(stype="kafka", ...)` | `KafkaOutput(...)` |
| `Stream(stype="kinesis", ...)` | `KinesisOutput(...)` |
| Side-effect CLI script | `build(profiles, output, **options)` |
| Mutable shared dictionary | Explicit shared `State` |
| `event.id == "1"` | `context.id == 1` |
| `event.time` as an ISO string | `context.time` as an aware `datetime` |
| `profile.birthdate` as an ISO string | `profile.birthdate` as a `date` |
| Local-time default | UTC default or an explicit IANA timezone |

## Known residual differences

The audit found no remaining high-severity accidental feature removal after
the 2.0.1 corrections. These lower-risk differences remain intentional:

- equal ordinary dictionaries do not share state automatically; use `State`;
- event definitions are mutable after construction, so callers should not
  assign unvalidated values to `rate`, `variance`, `limit`, or `schedule`;
- the old synchronous custom `send()` stream contract is replaced by the async
  `Output` lifecycle;
- profile loading uses the validated `load(path, limit=...)` interface rather
  than the overloaded 1.x `load(count, path)` call;
- empty profile and event collections now fail validation instead of silently
  producing no output;
- library execution no longer prints colored progress and completion messages.

## Conclusion

The important simulation capabilities from 1.6.0 are present in 2.0.1,
including persistent profile state, conditional scheduled work, event flows,
branching, grouping, profile persistence, console/Kafka/Kinesis outputs, and
live and batch execution.

The remaining differences are deliberate major-version changes or removals of
broken behavior. Any future removal of a behavior marked **Preserved** above
should be treated as a regression and accompanied by a failing test and
migration note.
