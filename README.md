# Faker Events
[![Python appliction](https://github.com/johnbrandborg/faker-events/workflows/Python%20application/badge.svg)](https://github.com/johnbrandborg/faker-events/actions?query=workflow%3A%22Python+application%22)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=johnbrandborg_faker-events&metric=alert_status)](https://sonarcloud.io/dashboard?id=johnbrandborg_faker-events)
[![PyPI version](https://badge.fury.io/py/Faker-Events.svg)](https://pypi.org/project/Faker-Events/)

Generates Events with formatted fake data for streams. The intention is for
 development and testing purposes without relying on real data.

## Usage
Faker Events allows you to create multiple data structures, and events that
occur randomly or schedule, after which are sent to a data stream or system,
through the message handler.

The structures can be defined as Python Dictionaries, and processed using a
function referred to as the profiler.

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

Set the "Events Per Minute" on the start method to change the maximum
allowed, but subject to system performance also.  The default is ~60 per
minute, but they are random so expect potentially lower rates.

If you want to see an example of this without writing code, run faker_events
from the command line.  For help in using the CLI use the -h parameter.

```shell
faker-events -n 10
```

Output
```json
{"event_time": "2022-05-19T22:43:39.683304", "type": "example", "event_id": "1", "user_id": "1009", "first_name": "Brandon", "last_name": "Braun", "spent": 0, "status": "normal"}
{"event_time": "2022-05-19T22:43:40.291519", "type": "example", "event_id": "2", "user_id": "1002", "first_name": "Jonathan", "last_name": "Keith", "spent": 0, "status": "normal"}
{"event_time": "2022-05-19T22:43:41.001050", "type": "example", "event_id": "3", "user_id": "1001", "first_name": "Lauren", "last_name": "Rodriguez", "spent": 0, "status": "normal"}
{"event_time": "2022-05-19T22:43:41.358616", "type": "example", "event_id": "4", "user_id": "1004", "first_name": "Joseph", "last_name": "Frank", "spent": 0, "status": "normal"}
{"event_time": "2022-05-19T22:43:42.356265", "type": "example", "event_id": "4", "user_id": "1004", "first_name": "Joseph", "last_name": "Frank", "spent": 71, "status": "normal"}
{"event_time": "2022-05-19T22:43:42.788833", "type": "example", "event_id": "6", "user_id": "1003", "first_name": "Nathaniel", "last_name": "Garrett", "spent": 0, "status": "normal"}
{"event_time": "2022-05-19T22:43:43.106967", "type": "example", "event_id": "7", "user_id": "1000", "first_name": "Jeffrey", "last_name": "Owens", "spent": 0, "status": "normal"}
{"event_time": "2022-05-19T22:43:43.754115", "type": "example", "event_id": "2", "user_id": "1002", "first_name": "Jonathan", "last_name": "Keith", "spent": 77, "status": "normal"}
{"event_time": "2022-05-19T22:43:44.121750", "type": "example", "event_id": "3", "user_id": "1001", "first_name": "Lauren", "last_name": "Rodriguez", "spent": 93, "status": "normal"}
```

If you would like to know more about how this Event Flow was created, read the
[Example documentation](docs/Example.MD).


#### Running a Faker Event Script

You can work with Faker Events interactively in Python, or you can just use
the class structures in a Python script, and call it using the command line
interface.

```shell
faker-events -s fake_users_flow.py -n 1
```

If you prefer to use Python diretly, use the `start` method on an
EventGenerator instance, to begin the steam.


#### Saving the Profile Data

The profile information created by Faker Events can be saved, so multiple runs
of the python script will contain the same profile details.

```shell
faker-events -s fake_users_flow.py -n 100 -p profiles.json
```

### Using Stream Handlers
Once you have installed Faker Events with the Stream type you want you
can now use a stream handler to send the JSON messages to Kakfa, or
Kinesis.

**Kafka**
```python
from faker_events import EventGenerator, Stream

example = Stream(stype='kafka', host='kafka:9092', name='example')
EventGenerator.set_stream(example)
```

**Kinesis**
```python
from faker_events import EventGenerator, Stream

example = Stream(stype='kinesis', name='example', key='key')
EventGenerator.set_stream(example)
```

Creating a custom Stream handler is easy.  Just create a Class that has a
`send` method, which takes the Dictionary of data, and then deliveries it.

**Custom Handler**
```python
class custom_stream():
    def __init__(self, *args, **kwargs):
        # Store Parameters and Connect to destination

    def send(self, message: Dict) -> None:
        # Do something with the message
```

### Starting a Batch
Create an Event Generator and use the batch method, with a start and finish
datetime object, and the frequncy like on the live stream.

```python
from datetime import datetime, timedelta

from faker_events import EventGenerator

start = datetime(2019, 1, 1)  # No one wants to relive 2020...
finish = start + timedelta(seconds=10)

EventGenerator.batch(start, finish)
```

## Data Points
### Event Data Points
The Event Type has some basic data points about the event that can be used
within the profiled method. (Access the Attribute using the 'event' within the
profiler)

* id - The id of the particular event, based on the event dictionary.
* time - The time the event occured (ISO Format).
* data - Event Data for updates or augmented assignments.

By default the Event time is local time.  Set the timezone on the generator
when required.

### Profile Data Points
When you use the Event Generator, the profiles you will use are created by the
Profile Generator.  Each profile holds a number of data points. Below is a
list of attributes that can be used on the 'profile' within the Event Profiler
function.

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
or us the 'start' or 'batch' methods that will handle the generator.

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

EventGenerator.set_first_events(Event(event, profiler))
```

## Event Sequences
#### Ordered
You can sequence the events by setting the next event to occur, and occurence
on how many times it will happen. To have events occur more than once, increase
the limit.

Either the 'next' attribute can be set with a statement, or the bitwise operator
can be use to set the next event.

```python
from faker_events import Event, EventGenerator

a = Event({'Name': 'A'})
b = Event({'Name': 'B'}, limit=2)
c = Event({'Name': 'C'})

a.next = b
b.next = c

# Short form:
# a >> b >> c

EventGenerator.set_first_events(a)
```

Output
```json
{"Name": "A"}
{"Name": "B"}
{"Name": "B"}
{"Name": "C"}
```

#### Grouping
If you need to two different events to be grouped together, you can set the
group_by parameter to true on the Event instance creation.  This will cause the
start and batch methods to send them together.

You can also use the '&' operator (rather than '>>') to set the next event but
grouped together so the event_time is the same.  Try not to mix the operators
into long mixed sequences as it can cause problems with the ordering.

### Persistant State
When creating event flows there is some concepts around how Faker Events works
that you should get familiar with.

1. The dictionary created is used only as a template for Events
2. Dictionaries that are identical will be treated as the same flow
3. Profile Functions should declare a puprose and what needs to be change
4. Event limit is for each profile created by the generator. (Default is 1)

The following example shows how we create a type of event with the dictionary
'customer', and then a flow in which a new customer event is made, followed by
a job change for the customer.

The generator has 2 profiles, and 1 of each event type, resulting in 4 events.
(Events with a limit of 0 will occur as long as the stream is running, without
 attempting to switch to the next event, even if one is set.)

```python
from faker_events import Event, EventGenerator
from faker import Faker

faker = Faker()

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

new_customer_event = Event(customer, new_customer)
customer_marriged_event = Event(customer, change_job)

new_customer_event >> customer_marriged_event

EventGenerator.set_first_events(new_customer_event)
```

Output (with two profiles)
```json
{"Name": "Ian", "Job": "Medical technical officer", "Created": "2021-09-28T15:13:55.809062", "Updated": "2021-09-28T15:13:55.809062"}
{"Name": "Eduardo", "Job": "Conservation officer, nature", "Created": "2021-09-28T15:13:56.316593", "Updated": "2021-09-28T15:13:56.316593"}
{"Name": "Ian", "Job": "Database administrator", "Created": "2021-09-28T15:13:55.809062", "Updated": "2021-09-28T15:13:56.773134"}
{"Name": "Eduardo", "Job": "Ergonomist", "Created": "2021-09-28T15:13:56.316593", "Updated": "2021-09-28T15:13:57.694891"}
```

If you need to update the details of the profile, or add persistant data from
the events you can do so within the Profiled method of the Event instance.
When using sequenced events, the profile can be used to retrieve the data from
previous events.

```python
from faker_events import Event, EventGenerator


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

a >> b >> c

EventGenerator.set_first_events(a)
```

Output
```json
{"Name": "A", "LastEvent": "none"}
{"Name": "B", "LastEvent": "EventA"}
{"Name": "C", "LastEvent": "EventB"}
```

### Multiple Event Flows
By grouping the events in lists, the Event Generator is able to work through
multiple Event Flows for each profile created, creating complex event streams.

```python
from faker_events import Event, EventGenerator

flow_a1 = Event({"Name": "A1"})
flow_aa1 = Event({"Name": "AA1"})
flow_aa2 = Event({"Name": "AA2"})

flow_b1 = Event({"Name": "B1"})
flow_bb1 = Event({"Name": "BB1"})
flow_bb2 = Event({"Name": "BB2"})

flow_a1 >> [flow_aa1, flow_aa2]
flow_b1 >> [flow_bb1, flow_bb2]

EventGeneratoe.set_first_events([flow_a1, flow_b1])
```

Output
```json
{"Name": "B1"}
{"Name": "BB2"}
{"Name": "A1"}
{"Name": "AA1"}
{"Name": "AA2"}
{"Name": "BB1"}
```

### To Do List
- [ ] Scheduling events with Cron syntax in Batch Mode.
- [ ] Edge Case testing to produce bad or corrupted data on purpose.

## License
Faker-Events is released under the MIT License. See the bundled LICENSE file for details.

## Credits
* [Daniele Faraglia](https://github.com/joke2k) & [Flavio Curella](https://github.com/fcurella) / [Faker](https://github.com/joke2k/faker)
