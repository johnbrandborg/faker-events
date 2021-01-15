"""
Main module for Faker-Events

Runs the Example EventType
"""

import faker_events


def main():
    """
    Main Function
    """
    event_generator = faker_events.EventGenerator()
    event_generator.live_stream()


if __name__ == '__main__':
    main()
