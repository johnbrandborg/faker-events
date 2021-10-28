"""
Main module for Faker-Events

Runs the Example EventType
"""

import asyncio
from faker_events import EventGenerator
from sys import stderr

event_generator = EventGenerator()


async def main():
    """
    Main Function if run as a module.  Example Events are generated to console.

    'python -m faker_events'
    """
    live_stream = asyncio.create_task(event_generator.live_stream())
    asyncio.create_task(event_generator.schedule())

    await live_stream

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print(f"\nStopping Event Stream.  {event_generator._total_count} in total generated.",
          file=stderr)
