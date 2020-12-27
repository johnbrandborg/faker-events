# faker-events (Planning)
Generates Events with formatted fake data for streams.

**NOTE** Don't use this software for anything but exploring use cases.
It is not tested, it is not quality controlled, and subject to breaking changes.

## Usage
Using Faker Events is a library, and doesn't come with a CLI.  This is in part
due to the Events you create being written in Python as objects.

This library utilises the Faker package to generate it's data on the profile.
Understanding how Faker works is recommended and you can find the documentation
for it [here](https://faker.readthedocs.io/en/stable/).

Install from GitHub  (No Packaging as it is only in Planning)
```bash
pip install git+https://github.com/johnbrandborg/faker-events
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

eg = faker_events.EventGenerator(1)

start = datetime(2019, 1, 1)  # No one wants to relive 2020...
finish = start + timedelta(seconds=10)

eg.batch(start, finish, 10)
```

### Creating a Custom Record
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

    def profiled(self, profile: dict ) -> dict:
        new_details = {
            'Always': fake.boolean(),
            'Profiled': profile.get('email'),
        }
        self.event.update(new_details)
        return self.event

eg = faker_events.EventGenerator(num_profile=2)
eg.events = NewEvent()
eg.live_stream()
```

### Event Sequences

You can sequence the events by setting the next event to occur, and occurence
on how many times it will happen.  If no limit is set, the next Event Type will
never be used.


```python
import faker_events

eg = faker_events.EventGenerator(1)

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

eg.events = a
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

## License

Faker-Events is released under the MIT License. See the bundled LICENSE file for details.

## Credits

* [Daniele Faraglia](https://github.com/joke2k) & [Flavio Curella](https://github.com/fcurella) / [Faker](https://github.com/joke2k/faker)
