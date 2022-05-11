"""
Main module for Faker-Events

Runs the Example EventType
"""

from argparse import ArgumentParser
import importlib
import os
import sys

from faker_events import EventGenerator
import faker_events.profiles


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
    try:
        sys.path.append(os.getcwd())
        module_path = args.script.rstrip(".py").replace("/", ".")
        event_script = importlib.import_module(module_path)
    except ModuleNotFoundError:
        print(f"No event module named '{args.script}'", file=sys.stderr)
        sys.exit(1)
else:
    import faker_events.example


try:
    event_generator.start()
except KeyboardInterrupt:
    print(f"\nStopping Event Stream.  {event_generator._total_count} in",
          "total generated.", file=sys.stderr)
