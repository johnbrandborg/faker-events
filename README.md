# Faker Events
[![Python appliction](https://github.com/johnbrandborg/faker-events/workflows/Python%20application/badge.svg)](https://github.com/johnbrandborg/faker-events/actions?query=workflow%3A%22Python+application%22)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=johnbrandborg_faker-events&metric=alert_status)](https://sonarcloud.io/dashboard?id=johnbrandborg_faker-events)
[![PyPI version](https://badge.fury.io/py/Faker-Events.svg)](https://pypi.org/project/Faker-Events/)

Generates Events with formatted fake data for streams. The intention is for
 development and testing purposes without relying on real data.

## Usage
Faker Events is a package that doesn't come with a CLI.  This is in part
due to the Events you create being written in Python as Dictionaries, and
processed using a function referred to as the profiler.

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
profiles are created.  Giving large numbers can take sometime to build.

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
{"event_time": "2021-09-28T14:05:31.520806", "type": "example", "event_id": 1, "user_id": 1008, "first_name": "Cindy", "last_name": "Bernard"}
{"event_time": "2021-09-28T14:05:31.997151", "type": "example", "event_id": 2, "user_id": 1003, "first_name": "Nicole", "last_name": "Mcneil"}
{"event_time": "2021-09-28T14:05:32.241834", "type": "example", "event_id": 3, "user_id": 1004, "first_name": "David", "last_name": "Berg"}
{"event_time": "2021-09-28T14:05:33.135551", "type": "example", "event_id": 4, "user_id": 1007, "first_name": "Kylie", "last_name": "Ortiz"}
{"event_time": "2021-09-28T14:05:33.265245", "type": "example", "event_id": 5, "user_id": 1006, "first_name": "Steven", "last_name": "Donaldson"}
{"event_time": "2021-09-28T14:05:34.159739", "type": "example", "event_id": 6, "user_id": 1005, "first_name": "Jennifer", "last_name": "Porter"}
{"event_time": "2021-09-28T14:05:34.722054", "type": "example", "event_id": 7, "user_id": 1009, "first_name": "Jason", "last_name": "York"}
{"event_time": "2021-09-28T14:05:35.054572", "type": "example", "event_id": 8, "user_id": 1002, "first_name": "Peter", "last_name": "Elliott"}
{"event_time": "2021-09-28T14:05:35.613473", "type": "example", "event_id": 9, "user_id": 1000, "first_name": "Tina", "last_name": "Nelson"}
{"event_time": "2021-09-28T14:05:36.166375", "type": "example", "event_id": 10, "user_id": 1001, "first_name": "Jason", "last_name": "Raymond"}
Event limit reached.  10 in total generated
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
within the profiled method. (Access the Attribute using the 'event' within the
profiler)

* id - The id of the particular event, based on the event dictionary.
* time - The time the event occured (ISO Format).
* data - Event Data for updates or augmented assignments.

### Profile Data Points

When you create the Event Generator, the profiles you will use in the events
are created with a number of data points. Below is a list of attributes that
can be used on the 'profile' within the Event Profiler function.

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

## Profiling Events

Creating an Event is as easy as just creating a dictionary that is passed into
the Event Class.  The Event Instance is then just set on the Event Generator,
and you can then use the 'create_events' method which will return a generator,
or us the 'live_stream' or 'batch' methods that will handle the generator.

If you want event values to be dynamic, create a profiler functions. The
function should take two arguments; event and profile.  These carry the attributes
listed above into the function for updating event values, or even creating new
key value pairs.

Update the event yourself by using 'event.data', which contains the dictionary
passed into the Event Class.  The other option is to return a dictionary with
the key value pairs you want to update.  The Event instance will handle updating
the values.

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

def profiler(event, profile):
    return {
        'Always': fake.boolean(),
        'Profiled': profile.email,
    }

eg = EventGenerator(num_profiles=2)
eg.first_events = Event(event, profiler)
eg.live_stream()
```

## Event Sequences

You can sequence the events by setting the next event to occur, and occurence
on how many times it will happen.  If no limit is set, the next Event Type will
never be used.

Either the 'next' attribute can be set with a statement, or the bitwise operator
can be use to set the next event.

```python
from faker_events import Event, EventGenerator

eg = EventGenerator(num_profiles=1)

a = Event({'Name': 'A'}, limit=1)
b = Event({'Name': 'B'}, limit=2)
c = Event({'Name': 'C'}, limit=1)

eg.first_events = a
a.next = b
b.next = c

# Short form:
# eg.first_events = a
# a >> b >> c

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

### Persistant State

When creating event flows there is some concepts around how Faker Events works
that you should get familiar with.

1. The dictionary created is used only as a template for Events
2. Dictionaries that are identical will be treated as the same flow
3. Profile Functions should declare a puprose and what needs to be change
4. Event limit is for each profile created by the generator.

The following example shows how we create a type of event with the dictionary
'customer', and then a flow in which a new customer event is made, followed by
a job change for the customer.

The generator has 2 profiles, and we as for 1 of each event type, resulting in
4 events. (Events with no limit will occur as long as the stream is running,
without attempting to switch to the next event, even if one is set.)

```python
from faker_events import EventGenerator, Event
from faker import Faker

faker = Faker()
eg = EventGenerator(num_profiles=2)

customer = {'Name': 'Unknown', 'Job': None, 'Created': None, 'Updated': None}

def new_customer(event, profile):
    return {
        "Name": profile.first_name,
        "Job": profile.job,
        "Created": event.time,
        "Updated": event.time
    }

def change_job(event, profile):
    return {
        "Job": faker.job(),
        "Updated": event.time
    }

new_customer_event = Event(customer, new_customer, limit=1)
customer_marriged_event = Event(customer, change_job, limit=1)

eg.first_events = new_customer_event
new_customer_event >> customer_marriged_event

eg.live_stream()
```

Output
```
{"Name": "Ian", "Job": "Medical technical officer", "Created": "2021-09-28T15:13:55.809062", "Updated": "2021-09-28T15:13:55.809062"}
{"Name": "Eduardo", "Job": "Conservation officer, nature", "Created": "2021-09-28T15:13:56.316593", "Updated": "2021-09-28T15:13:56.316593"}
{"Name": "Ian", "Job": "Database administrator", "Created": "2021-09-28T15:13:55.809062", "Updated": "2021-09-28T15:13:56.773134"}
{"Name": "Eduardo", "Job": "Ergonomist", "Created": "2021-09-28T15:13:56.316593", "Updated": "2021-09-28T15:13:57.694891"}
Event limit reached.  4 in total generated
```

If you need to update the details of the profile, or add persistant data from
the events you can do so within the Profiled method of the Event instance.
When using sequenced events, the profile can be used to retrieve the data from
previous events.

```python
from faker_events import EventGenerator, Event

eg = EventGenerator(num_profiles=1)

event_a = {'Name': 'A', 'LastEvent': 'none'}

def profiler_a(event, profile):
    profile.LastEvent = 'EventA'

event_b = {'Name': 'B', 'LastEvent': 'none'}

def profiler_b(event, profile):
    event.data['LastEvent'] = profile.LastEvent
    profile.LastEvent = 'EventB'

event_c = {'Name': 'C', 'LastEvent': 'none'}

def profiler_c(event, profile):
    event.data['LastEvent'] = profile.LastEvent

a = Event(event_a, profiler_a, 1)
b = Event(event_b, profiler_b, 1)
c = Event(event_c, profiler_c, 1)

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


### Multiple Event Flows

By grouping the events in lists, the Event Generator is able to work through
multiple Event Flows for each profile created, creating complex event streams.

```python
from faker_events import Event, EventGenerator

eg = EventGenerator(1)

flow_a1 = Event({"Name": "A1"}, limit=1)
flow_aa1 = Event({"Name": "AA1"}, limit=1)
flow_aa2 = Event({"Name": "AA2"}, limit=1)

flow_b1 = Event({"Name": "B1"}, limit=1)
flow_bb1 = Event({"Name": "BB1"}, limit=1)
flow_bb2 = Event({"Name": "BB2"}, limit=1)

eg.first_events = [flow_a1, flow_b1]
flow_a1 >> [flow_aa1, flow_aa2]
flow_b1 >> [flow_bb1, flow_bb2]

eg.live_stream()
```

Output
```
{"Name": "B1"}
{"Name": "BB2"}
{"Name": "A1"}
{"Name": "AA1"}
{"Name": "AA2"}
{"Name": "BB1"}
Event limit reached.  6 in total generated
```

## License

Faker-Events is released under the MIT License. See the bundled LICENSE file for details.

## Credits

* [Daniele Faraglia](https://github.com/joke2k) & [Flavio Curella](https://github.com/fcurella) / [Faker](https://github.com/joke2k/faker)
