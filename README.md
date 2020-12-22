# faker-events
Generates Events with formatted fake data for streams 

# Usage

## Starting a Stream
Create an Event Generator and start using Live Stream.

**Console**
```python
import faker_events

eg = faker_events.EventGenerator()
eg.live_stream()
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

## Event Sequences

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
No more events found.  4 in total generated
```
