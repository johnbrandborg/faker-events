from __future__ import annotations

import asyncio
import importlib
import sys
from collections.abc import Callable
from copy import deepcopy
from typing import Any, Protocol, runtime_checkable

import orjson


@runtime_checkable
class Output(Protocol):
    """Destination contract for generated events."""

    async def open(self) -> None: ...

    async def send(self, event: dict[str, Any]) -> None: ...

    async def close(self) -> None: ...


class ConsoleOutput:
    """Write newline-delimited JSON to stdout."""

    def __init__(self, *, pretty: bool = False) -> None:
        self._option = orjson.OPT_INDENT_2 if pretty else 0

    async def open(self) -> None:
        return None

    async def send(self, event: dict[str, Any]) -> None:
        payload = orjson.dumps(event, option=self._option) + b"\n"
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()

    async def close(self) -> None:
        return None


class MemoryOutput:
    """In-memory output useful for tests and embedding."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def open(self) -> None:
        return None

    async def send(self, event: dict[str, Any]) -> None:
        self.events.append(deepcopy(event))

    async def close(self) -> None:
        return None


class KafkaOutput:
    """High-throughput Kafka output backed by librdkafka."""

    def __init__(
        self,
        topic: str,
        bootstrap_servers: str,
        *,
        key: Callable[[dict[str, Any]], str | bytes | None] | None = None,
        **producer_config: Any,
    ) -> None:
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.key = key
        self.producer_config = producer_config
        self._producer: Any = None

    async def open(self) -> None:
        try:
            kafka = importlib.import_module("confluent_kafka")
        except ImportError as error:
            raise RuntimeError(
                "Kafka support requires: pip install 'faker-events[kafka]'"
            ) from error
        self._producer = kafka.Producer(
            {"bootstrap.servers": self.bootstrap_servers, **self.producer_config}
        )

    async def send(self, event: dict[str, Any]) -> None:
        if self._producer is None:
            raise RuntimeError("output is not open")

        loop = asyncio.get_running_loop()
        delivered: asyncio.Future[None] = loop.create_future()

        def callback(error: Any, _message: Any) -> None:
            if error is not None:
                loop.call_soon_threadsafe(
                    delivered.set_exception,
                    RuntimeError(f"Kafka delivery failed: {error}"),
                )
            else:
                loop.call_soon_threadsafe(delivered.set_result, None)

        event_key = self.key(event) if self.key else None
        while True:
            try:
                self._producer.produce(
                    self.topic,
                    value=orjson.dumps(event),
                    key=event_key,
                    callback=callback,
                )
                break
            except BufferError:
                await asyncio.to_thread(self._producer.poll, 0.1)

        self._producer.poll(0)
        await delivered

    async def close(self) -> None:
        if self._producer is not None:
            remaining = await asyncio.to_thread(self._producer.flush, 10)
            self._producer = None
            if remaining:
                raise RuntimeError(f"{remaining} Kafka messages were not delivered")


class KinesisOutput:
    """Buffered Kinesis output using PutRecords batches."""

    def __init__(
        self,
        stream_name: str,
        *,
        partition_key: Callable[[dict[str, Any]], str] | str = "faker-events",
        batch_size: int = 100,
        client: Any = None,
    ) -> None:
        if not 1 <= batch_size <= 500:
            raise ValueError("batch_size must be between 1 and 500")
        self.stream_name = stream_name
        self.partition_key = partition_key
        self.batch_size = batch_size
        self._client = client
        self._records: list[dict[str, Any]] = []

    async def open(self) -> None:
        if self._client is not None:
            return
        try:
            boto3 = importlib.import_module("boto3")
        except ImportError as error:
            raise RuntimeError(
                "Kinesis support requires: pip install 'faker-events[kinesis]'"
            ) from error
        self._client = boto3.client("kinesis")

    async def send(self, event: dict[str, Any]) -> None:
        if self._client is None:
            raise RuntimeError("output is not open")
        key = self.partition_key(event) if callable(self.partition_key) else self.partition_key
        self._records.append({"Data": orjson.dumps(event), "PartitionKey": key})
        if len(self._records) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        if not self._records:
            return
        client = self._client
        if client is None:
            raise RuntimeError("output is not open")
        records, self._records = self._records, []
        response = await asyncio.to_thread(
            client.put_records,
            StreamName=self.stream_name,
            Records=records,
        )
        failed = response.get("FailedRecordCount", 0)
        if failed:
            raise RuntimeError(f"Kinesis failed to deliver {failed} record(s)")

    async def close(self) -> None:
        await self.flush()
        self._client = None
