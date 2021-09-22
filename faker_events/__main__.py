"""
Main module for Faker-Events

Runs the Example EventType
"""

from faker_events import EventGenerator


def main():
    """
    Main Function
    """
    event_generator = EventGenerator()
    event_generator.live_stream()


if __name__ == '__main__':
    main()
