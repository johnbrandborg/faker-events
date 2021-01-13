# faker-events
[![Python appliction](https://github.com/johnbrandborg/faker-events/workflows/Python%20application/badge.svg)](https://github.com/johnbrandborg/faker-events/actions?query=workflow%3A%22Python+application%22)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=johnbrandborg_faker-events&metric=alert_status)](https://sonarcloud.io/dashboard?id=johnbrandborg_faker-events)
[![PyPI version](https://badge.fury.io/py/Faker-Events.svg)](https://pypi.org/project/Faker-Events/)

Generates Events with formatted fake data for streams. The intention is for
 development and testing purposes without relying on real data.

## Usage
Using Faker Events is a library, and doesn't come with a CLI.  This is in part
due to the Events you create being written in Python as objects.

This library utilises the Faker package to generate it's data on the profile.
Understanding how Faker works is recommended and you can find the documentation
for it [here](https://faker.readthedocs.io/en/stable/).

### Installation
By default faker-events simply prints to standard out.  To use a stream, give
the option when installing.

**Kafka**
```bash
pip install faker-events[kafka]
```

**Kinesis**
```bash
pip install faker-events[kinesis]
```

### Starting a Stream
Create an Event Generator and start using Live Stream. By default only 10
profiles are created.  Giving large numbers can take sometime to build so
becareful.

Set the "Events Per Minute" on the live_stream method to change the maximum
allowed, but subject to system performance also.  The default is ~60 per
minute, but they are random so expect potentially lower rates.

**Console**
```python
import faker_events

eg = faker_events.EventGenerator(num_profiles=100)
eg.live_stream(epm=120)
```

Output
```json
{"type": "example", "event_id": 1, "user_id": 1609288, "first_name": "David", "last_name": "Herrera"}
{"type": "example", "event_id": 2, "user_id": 1609288, "first_name": "David", "last_name": "Herrera"}
{"type": "example", "event_id": 3, "user_id": 500, "first_name": "Samantha", "last_name": "Sanchez"}
{"type": "example", "event_id": 4, "user_id": 500, "first_name": "Samantha", "last_name": "Sanchez"}
{"type": "example", "event_id": 5, "user_id": 500, "first_name": "Samantha", "last_name": "Sanchez"}
{"type": "example", "event_id": 6, "user_id": 1609288, "first_name": "David", "last_name": "Herrera"}
{"type": "example", "event_id": 7, "user_id": 500, "first_name": "Samantha", "last_name": "Sanchez"}
{"type": "example", "event_id": 8, "user_id": 1609288, "first_name": "David", "last_name": "Herrera"}
{"type": "example", "event_id": 9, "user_id": 500, "first_name": "Samantha", "last_name": "Sanchez"}
{"type": "example", "event_id": 10, "user_id": 500, "first_name": "Samantha", "last_name": "Sanchez"}
^C
Stopping Event Stream
```

### Using Stream Handlers

By default the JSON messages are only displayed on the standard output.  You
can however create a stream handler to send the JSON messages to Kakfa, or
Kinesis.

**Kafka**
```python
import faker_events

example = faker_events.Stream(stype='kafka', host='kafka:9092', name='example')
eg = faker_events.EventGenerator(stream=example)
eg.live_stream()
```

**Kinesis**
```python
import faker_events

example = faker_events.Stream(stype='kinesis', name='example', key='key')
eg = faker_events.EventGenerator(stream=example)
eg.live_stream()
```

### Starting a Batch
Create an Event Generator and use the batch method, with a start and finish
datetime object, and the frequncy like on the live stream.


```python
from datetime import datetime, timedelta

import faker_events

eg = faker_events.EventGenerator(num_profiles=1)

start = datetime(2019, 1, 1)  # No one wants to relive 2020...
finish = start + timedelta(seconds=10)

eg.batch(start, finish, epm=10)
```

## Data Points

### Event Data Points

The Event Type has some basic data points about the event that can be used
within the profiled method. (Access the Attribute using self)

* event_id - The id of the particular event
* event_time - The time the event occured (ISO Format)

### Profile Data Points

When you create the Event Generator, the profiles you will use in the events
are created with a number of data points. Below is a list of attributes that
can be used on the 'profile' object within the EventType Profiled method.

* id
* uuid
* username
* gender
* first_name
* last_name
* prefix_name
* suffix_name
* birthdate
* blood_group
* email
* employer
* job
* full_address1
* building_number1
* street_name1
* street_suffix1
* state1
* postcode1
* city1
* phone1
* full_address2
* building_number2
* street_name2
* street_suffix2
* state2
* postcode2
* city2
* phone2
* driver_license
* license_plate

## Creating a Custom Record
Create an Event Type that has an 'event' dictionary.  If you want values to be
processed for each event, create a function called 'profiled', and thats takes
a dict and returns an updated dict.

The profile is a randomly selected profile from the profiles created by the
Event Generator.  You can use details from the profile to build our events
that simulate customers, or entities.

```python
import faker
import faker_events

fake = faker.Faker()

class NewEvent(faker_events.EventType):
    event = {
        'Fixed': 'Doesnt Change',
        'Once': fake.color(),
        'Always': '',
        'Profiled': '',
    }

    def profiled(self, profile):
        new_details = {
            'Always': fake.boolean(),
            'Profiled': profile.email,
        }
        self.event.update(new_details)

eg = faker_events.EventGenerator(num_profiles=2)
eg.first_event = NewEvent()
eg.live_stream()
```

## Event Sequences

You can sequence the events by setting the next event to occur, and occurence
on how many times it will happen.  If no limit is set, the next Event Type will
never be used.


```python
import faker_events

eg = faker_events.EventGenerator(num_profiles=1)

class EventA(faker_events.EventType):
    event = {'Name': 'A'}

class EventB(faker_events.EventType):
    event = {'Name': 'B'}

class EventC(faker_events.EventType):
    event = {'Name': 'C'}

a = EventA(1)
b = EventB(2)
c = EventC(1)

a.next = b
b.next = c

eg.first_event = a
eg.live_stream()
```

**Output**
```
{"Name": "A"}
{"Name": "B"}
{"Name": "B"}
{"Name": "C"}
Event limited reached.  4 in total generated
```

### Using the Profile for Event State

If you need to update the details of the profile, or add persistant data from
the events you can do so within the Profiled method of the EventType instance.
When using sequenced events, the profile can be used to retrieve the data from
previous events.

```python
import faker_events

eg = faker_events.EventGenerator(num_profiles=1)

class EventA(faker_events.EventType):
    event = {'Name': 'A', 'LastEvent': 'none'}

    def profiled(self, profile):
        profile.LastEvent = self.__class__.__name__

class EventB(faker_events.EventType):
    event = {'Name': 'B', 'LastEvent': 'none'}

    def profiled(self, profile):
        self.event['LastEvent'] = profile.LastEvent
        profile.LastEvent = self.__class__.__name__

class EventC(faker_events.EventType):
    event = {'Name': 'C', 'LastEvent': 'none'}

    def profiled(self, profile):
        self.event['LastEvent'] = profile.LastEvent

a = EventA(1)
b = EventB(1)
c = EventC(1)

a.next = b
b.next = c

eg.first_event = a
eg.live_stream()
```

Output
```
{"Name": "A", "LastEvent": "none"}
{"Name": "B", "LastEvent": "EventA"}
{"Name": "C", "LastEvent": "EventB"}
Event limit reached.  3 in total generated
```

## License

Faker-Events is released under the MIT License. See the bundled LICENSE file for details.

## Credits

* [Daniele Faraglia](https://github.com/joke2k) & [Flavio Curella](https://github.com/fcurella) / [Faker](https://github.com/joke2k/faker)
