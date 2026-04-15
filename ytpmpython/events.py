"""
Event and timeline models used across parsers and renderers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    """
    Generic timeline event.

    Attributes:
        start: Start time in seconds.
        duration: Duration in seconds.
        type: Type string (e.g., "note", "tempo").
        meta: Arbitrary metadata dictionary (pitch, velocity, sample name, layer, effects).
    """
    start: float
    duration: float
    type: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NoteEvent(Event):
    """
    Note event (subclass of Event) convenience type.
    meta keys commonly used:
        pitch: MIDI note number (int)
        velocity: 0..127
        sample: sample name / path
        layer: layer name or index
    """
    def __init__(self, start: float, duration: float, pitch: int, velocity: int = 100,
                 sample: Optional[str] = None, layer: Optional[str] = None, **meta):
        data = {"pitch": pitch, "velocity": velocity, "sample": sample, "layer": layer}
        data.update(meta)
        super().__init__(start=start, duration=duration, type="note", meta=data)


@dataclass
class TempoEvent(Event):
    """
    Tempo event (BPM change).
    meta keys:
        bpm: float
    """
    def __init__(self, start: float, bpm: float):
        super().__init__(start=start, duration=0.0, type="tempo", meta={"bpm": bpm})


def sort_events(events: List[Event]) -> List[Event]:
    """Return events sorted by start time."""
    return sorted(events, key=lambda e: (e.start, -e.duration))