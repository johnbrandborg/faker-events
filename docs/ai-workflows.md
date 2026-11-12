# AI-assisted generation and analysis

Faker Events can support AI development in two directions:

1. use an LLM to help design realistic synthetic scenarios and domain text;
2. use an AI model to analyse the generated event stream.

Faker Events should remain the deterministic event engine. A model is best
used before generation or downstream from the stream, rather than called for
every event transform.

## Recommended architecture

```text
LLM-assisted scenario design
            |
            v
Profiles + Events + State ----> JSONL / Kafka / Kinesis
            |                              |
            |                              v
            |                  windows and aggregations
            |                              |
            v                              v
deterministic tests                 AI analysis model
```

This separation provides:

- repeatable event ordering and timing;
- explicit business rules and expected outcomes;
- controlled model cost and rate limits;
- easier testing and failure recovery;
- no remote model latency in the event hot path.

## Use an LLM to design a flow

An LLM can turn a business scenario into a first draft of profiles, states,
events, schedules, and assertions.

A useful prompt includes the v2 API constraints:

```text
Design a Faker Events v2 simulation for subscription billing.

Requirements:
- Activity events represent customer actions.
- Scheduled events represent system operations.
- Shared run-scoped data uses one explicit State object.
- Data that must survive separate runs belongs on Profile.
- Event transforms are synchronous and return a mapping, SKIP, or None.
- Use rate and fractional variance for activity timing.
- Use cron syntax for scheduled operations.
- Include deterministic pytest cases with a fixed seed and UTC batch range.

Return:
1. Event schemas.
2. State and profile fields.
3. Business invariants.
4. Python flow code.
5. Tests with expected event sequences.
```

Treat generated code as a draft. Review:

- whether state has the correct lifetime;
- whether money, counters, and status transitions follow domain rules;
- whether infinite flows have a bound;
- whether scheduled conditions cover both `SKIP` and delivery;
- whether emitted fields form a stable schema;
- whether deterministic tests prove the important outcomes.

## Generate structured fake data

Use Faker and explicit transforms for fields that can be generated locally:

```python
from faker import Faker
from faker_events import Event

fake = Faker()
fake.seed_instance(42)


def create_ticket(context, profile):
    return {
        "event_id": context.id,
        "event_time": context.time.isoformat(),
        "type": "support.ticket.created",
        "user_id": profile.id,
        "subject": fake.sentence(nb_words=6),
        "priority": fake.random_element(("low", "normal", "high")),
    }


ticket_created = Event(
    {"type": "support.ticket.created"},
    create_ticket,
    limit=2,
    rate=6,
    variance=0.25,
)
```

This is faster and more reproducible than asking an LLM to generate every
record.

## Add AI-generated domain text

Models are useful when a scenario needs richer unstructured text, such as
support conversations, product reviews, incident notes, or insurance claim
descriptions.

Generate and validate a reusable corpus before starting the stream:

```json
[
  {
    "category": "billing",
    "message": "My renewal was charged twice this month.",
    "sentiment": "negative"
  },
  {
    "category": "account",
    "message": "Please update the email address on my account.",
    "sentiment": "neutral"
  }
]
```

Load and sample the corpus in a transform:

```python
import json
import random
from pathlib import Path

messages = json.loads(Path("synthetic_support_messages.json").read_text())
randomizer = random.Random(42)


def add_message(context, profile):
    message = randomizer.choice(messages)
    return {
        "event_id": context.id,
        "event_time": context.time.isoformat(),
        "type": "support.message.received",
        "user_id": profile.id,
        **message,
    }
```

Validate model-generated corpora before use:

- require a JSON schema or typed model;
- reject missing, unexpected, or oversized values;
- remove accidental personal or confidential information;
- check category balance and duplicate content;
- store the approved corpus with an identifiable version;
- seed local sampling for repeatable runs.

## Why not call a model in every transform?

Event transforms are synchronous. A remote model call inside a transform
blocks event generation and can:

- destroy the configured timing rate;
- make virtual-time batches take minutes or hours;
- introduce nondeterministic failures and content;
- exceed model quotas or context limits;
- create unpredictable cost;
- expose profile or scenario data to an external provider.

Pre-generate model content, use a local deterministic corpus, or analyse
events downstream.

If runtime model inference is essential, isolate it behind a separate service
or stream consumer. That service can implement concurrency, retries, caching,
timeouts, and provider-specific rate limiting without coupling them to event
generation.

## Analyse a bounded batch

For a small evaluation, capture events in memory:

```python
from faker_events import EventGenerator, MemoryOutput

output = MemoryOutput()
generator = EventGenerator(profiles, events, output=output)
generator.batch(start, end)

events = output.events
```

Calculate exact facts in code before asking a model for interpretation:

```python
summary = {
    "event_count": len(events),
    "event_types": sorted({event["type"] for event in events}),
    "final_balance": events[-1]["balance"],
}
```

Then send the summary and a small, relevant sample to the chosen model:

```text
You are analysing a synthetic event simulation.

Known aggregate facts:
{summary}

Representative events:
{sample}

Identify:
1. unexpected state transitions;
2. suspicious ordering;
3. missing operational events;
4. useful follow-up assertions.

Do not recalculate the supplied aggregate facts. Return structured JSON.
```

Use normal code, SQL, or a dataframe for counts, sums, joins, and invariants.
Use the model for explanation, classification, anomaly hypotheses, and test
ideas. This reduces hallucinations and token usage.

## Analyse a continuous stream

For larger or continuous simulations:

1. send events to Kafka or Kinesis;
2. consume them in time or count windows;
3. calculate aggregates and select representative anomalies;
4. call the model once per window or anomaly;
5. write model findings to a separate topic or store.

Do not send every event individually unless the use case specifically tests
per-record inference capacity.

A typical analysis window might include:

```json
{
  "window_start": "2026-01-01T10:00:00Z",
  "window_end": "2026-01-01T10:05:00Z",
  "event_count": 1482,
  "failed_payments": 37,
  "expired_sessions": 16,
  "unexpected_transitions": [
    {
      "user_id": "1042",
      "from": "cancelled",
      "to": "active"
    }
  ]
}
```

This is cheaper, faster, and usually more useful than passing raw event
history into a model.

## Build AI evaluation datasets

Faker Events can create repeatable datasets for evaluating agents, classifiers,
fraud models, anomaly detectors, and observability assistants.

Include explicit ground truth in the scenario:

```python
def suspicious_payment(context, profile):
    context.state["balance"] -= 5_000
    return {
        "type": "payment.sent",
        "user_id": profile.id,
        "amount": 5_000,
        "expected_label": "suspicious",
        "scenario_id": "large-transfer-001",
    }
```

Recommended evaluation fields:

- stable `scenario_id`;
- expected label or outcome;
- profile or entity ID;
- timezone-aware event time;
- event sequence number where required;
- model input fields;
- fields excluded from model input but retained as ground truth.

Keep the generator seed, profile corpus, AI-generated text corpus version,
simulation range, and expected assertions with the dataset. These values make
failures reproducible.

## Privacy and safety

Synthetic generation lowers privacy risk but does not remove it automatically:

- never seed prompts with copied production records;
- do not include real secrets, tokens, account numbers, or endpoints;
- review model-generated text for accidental real names and contact details;
- use isolated test destinations rather than production streams;
- apply retention and access controls to generated datasets;
- record the model and prompt version when generated content affects an
  evaluation;
- validate model output before it enters an event schema.

Faker Events creates plausible synthetic records; it does not guarantee that a
randomly generated value cannot resemble a real person or identifier.

## Choosing a pattern

| Goal | Recommended pattern |
|---|---|
| Draft a realistic business flow | Ask an LLM for schemas, rules, code, and tests; review before running. |
| Produce high-volume structured events | Use Faker, deterministic transforms, and `State`. |
| Add rich synthetic text | Pre-generate a validated corpus with a model and sample it locally. |
| Explain a small batch | Compute facts locally, then send summaries and selected events to a model. |
| Analyse a live stream | Use Kafka or Kinesis, aggregate in a consumer, then call the model. |
| Evaluate an AI system | Generate deterministic scenarios with explicit ground truth and stable IDs. |
