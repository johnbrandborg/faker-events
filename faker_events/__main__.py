"""
Main module for Faker-Events

Runs the Example EventType
"""

from faker_events import EventGenerator


def main():
    """
    Main Function if run as a module.  Example Events are generated to console.

    'python -m faker_events'
    """
    event_generator = EventGenerator()
    event_generator.live_stream()


if __name__ == '__main__':
    main()
