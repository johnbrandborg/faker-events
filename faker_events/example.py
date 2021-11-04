"""
An example of Event creation.
"""

from faker_events import Event, EventGenerator

structure = {
    'event_time': '',
    'type': 'example',
    'event_id': '',
    'user_id': '',
    'first_name': '',
    'last_name': ''
}


def profiler_example(event, profile: dict) -> dict:
    return {
        'event_time': event.time,
        'event_id': event.id,
        'user_id': profile.id,
        'first_name': profile.first_name,
        'last_name': profile.last_name
    }


event = Event(structure, profiler_example, 10)
EventGenerator.set_first_events(event)
