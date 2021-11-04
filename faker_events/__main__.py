"""
Main module for Faker-Events

Runs the Example EventType
"""

from argparse import ArgumentParser
import asyncio
from faker_events import EventGenerator
import faker_events.profiles
import importlib
from sys import stderr

parser = ArgumentParser(prog="python -m faker_events",
                        description="Faker Events creates JSON events, and"
                                    " can direct them to Data Streams.")
parser.add_argument("-n", "--nprofiles",
                    type=int,
                    default=10,
                    dest="num_profiles",
                    help="The number of profiles to create")
parser.add_argument("-s", "--script",
                    type=str,
                    metavar="FILE",
                    dest="script",
                    help="Event Script to be loaded")
args = parser.parse_args()

faker_events.profiles.load(args.num_profiles)
event_generator = EventGenerator()

if args.script:
    faker_events = importlib.import_module(args.script)
else:
    import faker_events.example


async def main():
    """
    Main Function if run as a module.  Example Events are generated to console.

    'python -m faker_events'
    """

    event_generator.first_events = faker_events.example.example

    live_stream = asyncio.create_task(event_generator.live_stream())
    asyncio.create_task(event_generator.schedule())

    await live_stream

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print(f"\nStopping Event Stream.  {event_generator._total_count} in total generated.",
          file=stderr)
