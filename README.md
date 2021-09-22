# Faker Events
[![Python appliction](https://github.com/johnbrandborg/faker-events/workflows/Python%20application/badge.svg)](https://github.com/johnbrandborg/faker-events/actions?query=workflow%3A%22Python+application%22)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=johnbrandborg_faker-events&metric=alert_status)](https://sonarcloud.io/dashboard?id=johnbrandborg_faker-events)
[![PyPI version](https://badge.fury.io/py/Faker-Events.svg)](https://pypi.org/project/Faker-Events/)

Generates Events with formatted fake data for streams. The intention is for
 development and testing purposes without relying on real data.

## Usage
Faker Events is a package that doesn't come with a CLI.  This is in part
due to the Events you create being written in Python as objects.

The Faker package is utilised to generate the data on the profiles.
Understanding how Faker works is recommended and you can find the documentation
for it [here](https://faker.readthedocs.io/en/stable/).

Beyond the profiles though for the custom event types any python data
generation software can be used.

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

**Standard Output**
```python
import faker_events

eg = faker_events.EventGenerator(num_profiles=100)
eg.live_stream(epm=120)
```

Output
```json
{"type": "example", "event_time": "2021-01-14T19:10:02.678866", "event_id": 1, "first_name": "John", "last_name": "Harris"}
{"type": "example", "event_time": "2021-01-14T19:10:03.468144", "event_id": 2, "first_name": "Robert", "last_name": "Lane"}
{"type": "example", "event_time": "2021-01-14T19:10:04.270969", "event_id": 3, "first_name": "Michelle", "last_name": "Clayton"}
{"type": "example", "event_time": "2021-01-14T19:10:04.888072", "event_id": 4, "first_name": "Robert", "last_name": "Lane"}
{"type": "example", "event_time": "2021-01-14T19:10:05.446477", "event_id": 5, "first_name": "Andrew", "last_name": "Oconnor"}
^C
Stopping Event Stream
```

If you want to see a demo of  this without writing code, run faker_events as a
 module from the command line.

```bash
python -m faker_events
```

### Using Stream Handlers

Once you have installed Faker Events with the Stream type you want you
can now use a stream handler to send the JSON messages to Kakfa, or
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
can be used on the 'profile' object within the Event Profiler function.

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
from faker import Faker
from faker_events import Event, EventGenerator

fake = Faker()

event = {
    'Fixed': 'Doesnt Change',
    'Once': fake.color(),
    'Always': '',
    'Profiled': '',
}

def profiler(self, profile):
    return {
        'Always': fake.boolean(),
        'Profiled': profile.email,
    }

eg = EventGenerator(num_profiles=2)
eg.first_event = Event(event, profiler)
eg.live_stream()
```

## Event Sequences

You can sequence the events by setting the next event to occur, and occurence
on how many times it will happen.  If no limit is set, the next Event Type will
never be used.

```python
from faker_events import Event, EventGenerator

eg = EventGenerator(num_profiles=1)

a = Event({'Name': 'A'}, limit=1)
b = Event({'Name': 'B'}, limit=2)
c = Event({'Name': 'C'}, limit=1)

eg.first_events = a
a >> b >> c

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
the events you can do so within the Profiled method of the Event instance.
When using sequenced events, the profile can be used to retrieve the data from
previous events.

```python
from faker_events import EventGenerator, Event

eg = EventGenerator(num_profiles=1)

event_a = {'Name': 'A', 'LastEvent': 'none'}

def profile_a(self, profile):
    profile.LastEvent = self.__class__.__name__

event_b = {'Name': 'B', 'LastEvent': 'none'}

def profile_b(self, profile):
    self.event['LastEvent'] = profile.LastEvent
    profile.LastEvent = self.__class__.__name__

event_c = {'Name': 'C', 'LastEvent': 'none'}

def profile_c(self, profile):
    self.event['LastEvent'] = profile.LastEvent

a = Event(event_a, profile_a, 1)
b = Event(event_b, profile_b, 1)
c = Event(event_c, profile_c, 1)

eg.first_events = a
a >> b >> c

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
