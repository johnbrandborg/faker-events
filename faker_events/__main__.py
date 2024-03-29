"""
Main module for Faker-Events

Runs the Example EventType
"""

from argparse import ArgumentParser, Namespace
import importlib
import os
import sys

from faker_events import EventGenerator, ProfileGenerator
from faker_events.text_color import eprint, Palatte


parser = ArgumentParser(prog="python -m faker_events",
                        description="Faker Events creates JSON events, and"
                                    " can direct them to Data Streams.")
parser.add_argument("-n", "--nprofiles",
                    type=int,
                    default=1,
                    dest="num_profiles",
                    help="The number of profiles to create")
parser.add_argument("-p", "--profiles",
                    type=str,
                    metavar="FILE",
                    dest="profiles_file",
                    help="Profiles files to be used")
parser.add_argument("-s", "--script",
                    type=str,
                    metavar="FILE",
                    dest="script",
                    help="Event Script to be loaded.")
parser.add_argument("-u", "--update",
                    action='store_true',
                    dest="update_profiles",
                    help="Save profile data on completion")


def cli(args: Namespace):
    profiles_generator = ProfileGenerator()
    profiles_generator.load(args.num_profiles, args.profiles_file)
    event_generator = EventGenerator(profiles_generator)

    if args.script:
        try:
            sys.path.append(os.getcwd())
            module_path = os.path.splitext(args.script)[0].replace("/", ".")
            importlib.import_module(module_path)
        except ModuleNotFoundError:
            eprint(f"ERROR: No event module named '{args.script}'",
                   Palatte.RED)
            return 1
    else:
        import faker_events.example  # noqa

    try:
        event_generator.start()
    except KeyboardInterrupt:
        eprint(f"\nStopping Event Stream.  {event_generator._total_count} in "
               "total generated.", Palatte.BLUE)
    finally:
        if args.update_profiles:
            eprint(f"Updating the profiles data to {args.profiles_file}",
                   Palatte.BLUE)
            profiles_generator.save(args.profiles_file)


if __name__ == "__main__":
    sys.exit(cli(parser.parse_args()))
