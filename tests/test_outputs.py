import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from faker_events import ConsoleOutput, KafkaOutput, KinesisOutput, MemoryOutput


@pytest.mark.asyncio
async def test_console_output_writes_json_lines(capsys) -> None:
    output = ConsoleOutput()

    await output.open()
    await output.send({"valid": True})
    await output.close()

    assert capsys.readouterr().out == '{"valid":true}\n'


@pytest.mark.asyncio
async def test_memory_output_copies_events() -> None:
    output = MemoryOutput()
    event = {"value": 1}

    await output.send(event)
    event["value"] = 2

    assert output.events == [{"value": 1}]


@pytest.mark.asyncio
async def test_kinesis_batches_and_flushes() -> None:
    client = Mock()
    client.put_records.return_value = {"FailedRecordCount": 0}
    output = KinesisOutput("events", batch_size=2, client=client)

    await output.open()
    await output.send({"id": 1})
    client.put_records.assert_not_called()
    await output.send({"id": 2})
    await output.close()

    client.put_records.assert_called_once()
    request = client.put_records.call_args.kwargs
    assert request["StreamName"] == "events"
    assert len(request["Records"]) == 2


@pytest.mark.asyncio
async def test_kinesis_surfaces_delivery_failure() -> None:
    client = Mock()
    client.put_records.return_value = {"FailedRecordCount": 1}
    output = KinesisOutput("events", batch_size=1, client=client)

    await output.open()
    with pytest.raises(RuntimeError, match="failed to deliver"):
        await output.send({"id": 1})


def test_kinesis_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        KinesisOutput("events", batch_size=501)


@pytest.mark.asyncio
async def test_kafka_delivers_and_flushes(monkeypatch) -> None:
    producer = Mock()
    producer.flush.return_value = 0

    def produce(_topic, *, value, key, callback) -> None:
        assert value == b'{"id":1}'
        assert key == "1"
        callback(None, Mock())

    producer.produce.side_effect = produce
    producer_type = Mock(return_value=producer)
    monkeypatch.setitem(
        sys.modules,
        "confluent_kafka",
        SimpleNamespace(Producer=producer_type),
    )
    output = KafkaOutput("events", "broker:9092", key=lambda event: str(event["id"]))

    await output.open()
    await output.send({"id": 1})
    await output.close()

    producer_type.assert_called_once()
    producer.flush.assert_called_once_with(10)


@pytest.mark.asyncio
async def test_outputs_must_be_opened() -> None:
    with pytest.raises(RuntimeError, match="not open"):
        await KafkaOutput("events", "broker:9092").send({})
    with pytest.raises(RuntimeError, match="not open"):
        await KinesisOutput("events").send({})
