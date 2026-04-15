"""
Event models for timeline-driven rendering.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class Event:
    start: float
    duration: float
    type: str = "event"
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NoteEvent(Event):
    def __init__(self, start: float, duration: float, pitch: int, velocity: int = 100, sample: str | None = None, layer: str | None = None, **meta):
        data = {"pitch": pitch, "velocity": velocity, "sample": sample, "layer": layer}
        data.update(meta)
        super().__init__(start=start, duration=duration, type="note", meta=data)

@dataclass
class TempoEvent(Event):
    def __init__(self, start: float, bpm: float):
        super().__init__(start=start, duration=0.0, type="tempo", meta={"bpm": float(bpm)})