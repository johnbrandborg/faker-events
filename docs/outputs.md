# Outputs

Outputs deliver generated event dictionaries to a destination. Faker Events
includes console, memory, Kafka, and Kinesis outputs and supports custom async
destinations.

Pass an output to the generator:

```python
generator = EventGenerator(profiles, events, output=output)
```

`run_live()`, `run_batch()`, `start()`, and `batch()` manage the output
lifecycle:

1. call `open()`;
2. call `send(event)` for every delivered event;
3. call `close()`, including when generation raises an exception.

`generate()` and `iter_batch()` yield events without using the configured
output.

## Console output

`ConsoleOutput` writes UTF-8 JSON to standard output:

```python
from faker_events import ConsoleOutput

output = ConsoleOutput()
```

The default is compact JSON Lines, one event per line. This is suitable for
pipes and ingestion tools:

```shell
faker-events run flow.py | consumer
```

Use `ConsoleOutput(pretty=True)` or the CLI's `--pretty` option for indented
human-readable output. Pretty output can span multiple lines and is not JSON
Lines.

Serialization uses `orjson`. Event values must therefore be JSON
serializable.

## Memory output

`MemoryOutput` stores deep-copy snapshots in `events`:

```python
from faker_events import MemoryOutput

output = MemoryOutput()
generator = EventGenerator(profiles, events, output=output)
generator.batch(start, end)

assert output.events[0]["type"] == "account.opened"
```

It is useful for tests, notebooks, and embedding. Mutating an original event
after delivery does not change the stored snapshot.

## Kafka

Install the optional adapter:

```shell
pip install "faker-events[kafka]"
```

Create an output with a topic and bootstrap servers:

```python
from faker_events import KafkaOutput

output = KafkaOutput(
    "customer-events",
    "broker-1:9092,broker-2:9092",
    key=lambda event: event["customer_id"],
)
```

The key callable may return `str`, `bytes`, or `None`.

Additional keyword arguments are passed to
`confluent_kafka.Producer`. Configuration names containing dots can be
expanded from a dictionary:

```python
output = KafkaOutput(
    "customer-events",
    "broker:9093",
    **{
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": username,
        "sasl.password": password,
    },
)
```

Each `send()` waits for the broker delivery callback. Local queue pressure is
handled by polling and retrying the enqueue. `close()` waits up to ten seconds
for queued messages and raises if any remain undelivered. Broker delivery
errors are surfaced as `RuntimeError`.

Secrets should come from environment variables or a secret manager, not from
source-controlled flow files.

## Kinesis

Install the optional adapter:

```shell
pip install "faker-events[kinesis]"
```

Create an output with a stream name:

```python
from faker_events import KinesisOutput

output = KinesisOutput(
    "customer-events",
    partition_key=lambda event: event["customer_id"],
    batch_size=100,
)
```

`partition_key` can be a fixed string or a callable returning a string.
`batch_size` must be from 1 to 500 and defaults to 100.

The adapter creates a standard `boto3` Kinesis client, so credentials, region,
and endpoint resolution follow the normal boto3 configuration chain.

Records are buffered until `batch_size` is reached. `close()` flushes any
remaining records with `PutRecords`.

If AWS reports failed records, the adapter raises `RuntimeError`. It does not
automatically retry individual failed records. Use an output wrapper or a
custom output when the application requires a particular retry, dead-letter,
or idempotency policy.

Tests and applications with an existing client can inject it:

```python
output = KinesisOutput("customer-events", client=kinesis_client)
```

## Custom outputs

A custom output implements three async methods:

```python
from typing import Any


class DatabaseOutput:
    async def open(self) -> None:
        self.connection = await connect()

    async def send(self, event: dict[str, Any]) -> None:
        await self.connection.insert(event)

    async def close(self) -> None:
        await self.connection.close()
```

Faker Events uses structural typing, so inheriting from `Output` is optional.
The object only needs compatible `open`, `send`, and `close` methods.

Avoid blocking network or file calls directly in these methods. Use an async
client or move blocking work to a thread with `asyncio.to_thread()`.

An exception from `open()` stops execution. An exception from `send()` stops
delivery and then closes the output. An exception from `close()` is propagated
to the caller.

## Delivery considerations

Faker Events does not add transaction IDs, retries, deduplication, or
exactly-once guarantees. Put identifiers needed by the destination in the
event schema and configure retry behavior according to the target system.

For high-volume production-like tests, validate destination quotas, message
size limits, partition distribution, and failure handling before increasing
event rates.
