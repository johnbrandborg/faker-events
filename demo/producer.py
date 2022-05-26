"""
Creates a stream of floating points into Kafka, using Faker Events.
"""

from sys import exit as sys_exit
from random import uniform
import webbrowser

from faker_events import Event, EventGenerator, Stream

if __name__ == "__main__":
    print("Do not run me as a module. This is a Faker Events script")
    sys_exit(1)

kafka_stream = Stream(stype="kafka", host="kafka", name="test")
EventGenerator.set_stream(kafka_stream)

machine_telemetry = Event(
    data={"Value": 0.0},
    profiler=lambda e, p: {"Value": uniform(0, 100)},
    limit=0,
    epm=200
)

EventGenerator.set_first_events(machine_telemetry)

webbrowser.open("http://localhost:9000")
