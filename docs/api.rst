.. _api-reference:

=============
API Reference
=============

Events and generation
=====================

.. autoclass:: faker_events.Event
   :members:
   :undoc-members:

.. autoclass:: faker_events.EventGenerator
   :members:
   :undoc-members:

.. autoclass:: faker_events.EventContext
   :members:
   :undoc-members:

.. autoclass:: faker_events.GeneratedEvent
   :members:
   :undoc-members:

.. autoclass:: faker_events.GeneratorConfig
   :members:
   :undoc-members:

``SKIP`` is the public sentinel returned by a transform when no event should be
delivered for that processing attempt.

State and profiles
==================

.. autoclass:: faker_events.State
   :members:
   :undoc-members:

.. autoclass:: faker_events.Profile
   :members:
   :undoc-members:

.. autoclass:: faker_events.ProfileGenerator
   :members:
   :undoc-members:

Outputs
=======

.. autoclass:: faker_events.Output
   :members:
   :undoc-members:

.. autoclass:: faker_events.ConsoleOutput
   :members:
   :undoc-members:

.. autoclass:: faker_events.MemoryOutput
   :members:
   :undoc-members:

.. autoclass:: faker_events.KafkaOutput
   :members:
   :undoc-members:

.. autoclass:: faker_events.KinesisOutput
   :members:
   :undoc-members:
