# Faker Events

[![CI](https://github.com/johnbrandborg/faker-events/actions/workflows/python-app.yml/badge.svg)](https://github.com/johnbrandborg/faker-events/actions/workflows/python-app.yml)
[![Documentation](https://readthedocs.org/projects/faker-events/badge/?version=latest)](https://faker-events.readthedocs.io/en/latest/)
[![PyPI](https://img.shields.io/pypi/v/faker-events.svg)](https://pypi.org/project/faker-events/)
[![Python](https://img.shields.io/pypi/pyversions/faker-events.svg)](https://pypi.org/project/faker-events/)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=faker-events&metric=alert_status&branch=main)](https://sonarcloud.io/summary/new_code?id=faker-events&branch=main)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=faker-events&metric=coverage&branch=main)](https://sonarcloud.io/summary/new_code?id=faker-events&branch=main)
[![License](https://img.shields.io/pypi/l/faker-events.svg)](https://github.com/johnbrandborg/faker-events/blob/main/LICENSE)

Generate realistic, stateful event streams for development, demos, load tests,
AI evaluation, and data-pipeline validation without copying production data.

Faker Events models human activity and scheduled system operations against
isolated per-profile state. It supports deterministic generation, virtual-time
batches, cron schedules, JSON Lines, Kafka, Kinesis, and custom async outputs.

## Install

```shell
pip install faker-events
```

Optional output adapters:

```shell
pip install "faker-events[kafka]"
pip install "faker-events[kinesis]"
```

## Quickstart

Run the built-in stateful account simulation:

```shell
faker-events run --profiles 10 --max-events 100 --seed 42
```

Run the savings and scheduled-fee example in virtual time:

```shell
faker-events run examples/savings.py --profiles 1 \
  --start 2026-01-01T00:00:00+00:00 \
  --end 2026-01-01T00:02:00+00:00
```

## Documentation

The complete user guide, API reference, examples, AI workflows, and v1
migration guide are available on
[Read the Docs](https://faker-events.readthedocs.io/en/latest/).

## License

Faker Events is released under the [MIT License](LICENSE).
