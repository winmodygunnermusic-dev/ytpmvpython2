"""
MIDI parser implementation. Uses `mido` if available.
Converts MIDI note-on/note-off and tempo events to Event objects.

This parser is defensive: if mido is missing, it raises ImportError with guidance.
"""

from typing import List
from ..events import Event, NoteEvent, TempoEvent
from .base import register_parser, BaseParser
import logging

logger = logging.getLogger(__name__)

@register_parser("midi")
class MidiParser(BaseParser):
    """
    MIDI parser that converts MIDI tracks to note events.

    Requires the `mido` package (pip install mido python-rtmidi optional).
    """

    def __init__(self):
        try:
            import mido  # type: ignore
            self.mido = mido
        except Exception as exc:
            raise ImportError("mido is required for MidiParser: pip install mido") from exc

    def parse(self, path: str) -> List[Event]:
        mid = self.mido.MidiFile(path)
        events: List[Event] = []
        ticks_per_beat = mid.ticks_per_beat or 480
        current_time = 0.0
        tempo = 500000  # default microseconds per beat
        tempo_map = [(0.0, tempo)]
        for track in mid.tracks:
            abs_time = 0
            # We'll keep per-track note-on dictionary to assemble durations
            note_on_times = {}  # (channel, note) -> abs_time
            for msg in track:
                abs_time += msg.time
                current_seconds = self.mido.tick2second(abs_time, ticks_per_beat, tempo)
                if msg.type == "set_tempo":
                    tempo = msg.tempo
                    tempo_map.append((current_seconds, tempo))
                    events.append(TempoEvent(start=current_seconds, bpm=60000000.0 / tempo))
                elif msg.type == "note_on" and msg.velocity > 0:
                    note_on_times[(getattr(msg, "channel", 0), msg.note)] = current_seconds
                elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                    key = (getattr(msg, "channel", 0), msg.note)
                    t0 = note_on_times.pop(key, None)
                    if t0 is not None:
                        duration = max(0.0, current_seconds - t0)
                        events.append(NoteEvent(start=t0, duration=duration, pitch=msg.note,
                                                velocity=getattr(msg, "velocity", 0),
                                                sample=None, layer=f"midi_{getattr(msg, 'channel', 0)}"))
        logger.debug("Parsed %d events from MIDI %s", len(events), path)
        return events