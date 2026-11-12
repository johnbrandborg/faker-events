"""Generate realistic, stateful event streams without production data."""

from .__about__ import __version__
from .engine import SKIP, Event, EventGenerator
from .models import EventContext, GeneratedEvent, GeneratorConfig, Profile
from .outputs import ConsoleOutput, KafkaOutput, KinesisOutput, MemoryOutput, Output
from .profile_factory import ProfileGenerator

__all__ = [
    "SKIP",
    "ConsoleOutput",
    "Event",
    "EventContext",
    "EventGenerator",
    "GeneratedEvent",
    "GeneratorConfig",
    "KafkaOutput",
    "KinesisOutput",
    "MemoryOutput",
    "Output",
    "Profile",
    "ProfileGenerator",
    "__version__",
]
