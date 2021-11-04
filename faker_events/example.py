"""
An example of Event creation.
"""

from faker_events import Event

example_event = {
    'event_time': '',
    'type': 'example',
    'event_id': '',
    'user_id': '',
    'first_name': '',
    'last_name': ''
}


def _profiler_example(event, profile: dict) -> dict:
    return {
        'event_time': event.time,
        'event_id': event.id,
        'user_id': profile.id,
        'first_name': profile.first_name,
        'last_name': profile.last_name
    }


example = Event(example_event, _profiler_example, 10)
