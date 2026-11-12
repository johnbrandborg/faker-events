============
Faker Events
============

Release v\ |version|

.. image:: https://img.shields.io/pypi/v/faker-events
   :target: https://pypi.org/project/faker-events/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/faker-events?logo=python&logoColor=FFE873
   :target: https://pypi.org/project/faker-events/
   :alt: Supported Python Versions

.. image:: https://github.com/johnbrandborg/faker-events/actions/workflows/python-app.yml/badge.svg
   :target: https://github.com/johnbrandborg/faker-events/actions/workflows/python-app.yml
   :alt: CI Status

.. image:: https://readthedocs.org/projects/faker-events/badge/?version=latest
   :target: https://faker-events.readthedocs.io/en/latest/
   :alt: Documentation Status

.. image:: https://img.shields.io/pypi/l/faker-events.svg
   :target: https://github.com/johnbrandborg/faker-events/blob/main/LICENSE
   :alt: License

**Faker Events** generates realistic, stateful event streams for development,
demos, load tests, and data-pipeline validation without copying production
data.

Model human activity and scheduled system operations against shared
per-profile state, then deliver immutable event snapshots to JSON Lines,
Kafka, Kinesis, or a custom destination.

Quickstart
----------

Install from PyPI:

.. code-block:: console

   $ pip install faker-events

Create profiles and a stateful flow:

.. code-block:: python

   from faker_events import Event, EventGenerator, ProfileGenerator, State

   profiles = ProfileGenerator(seed=42).create(10)
   account = State({"balance": 0})

   def deposit(context, profile):
       context.state["balance"] += 100
       return {
           "type": "account.deposit",
           "user_id": profile.id,
           "balance": context.state["balance"],
       }

   deposited = Event(
       {"type": "account.deposit"},
       deposit,
       state=account,
       rate=12,
       variance=0.25,
   )

   EventGenerator(profiles, deposited).start()

Or run the built-in example:

.. code-block:: console

   $ faker-events run --profiles 10 --max-events 100 --seed 42

Explore
-------

.. grid:: 1 2 2 2
   :gutter: 3

   .. grid-item-card:: Events and flows
      :link: events-and-flows
      :link-type: doc

      Define transforms, sequences, branches, grouping, limits, and shared
      event state.

   .. grid-item-card:: Timing and schedules
      :link: event-timing
      :link-type: doc

      Configure independent event pacing, random variance, virtual time, and
      deterministic generation.

   .. grid-item-card:: State and profiles
      :link: state-lifecycle
      :link-type: doc

      Choose the correct lifecycle for run-scoped state and durable entity
      fields.

   .. grid-item-card:: Outputs
      :link: outputs
      :link-type: doc

      Deliver events to the console, memory, Kafka, Kinesis, or a custom async
      destination.

   .. grid-item-card:: AI workflows
      :link: ai-workflows
      :link-type: doc

      Design scenarios with an LLM, enrich synthetic data, analyse streams,
      and build deterministic AI evaluation datasets.

User guide
----------

.. toctree::
   :maxdepth: 2

   events-and-flows
   event-timing
   state-lifecycle
   state-and-schedules
   scheduling
   profiles
   outputs
   ai-workflows
   cli
   testing

Upgrading and reference
-----------------------

.. toctree::
   :maxdepth: 2

   migrating-from-v1
   api

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
