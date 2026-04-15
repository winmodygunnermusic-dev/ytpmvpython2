"""
MIDI parser using mido (optional).
"""

from typing import List
from ..events import Event, NoteEvent, TempoEvent
from .base import register_parser, BaseParser
import logging

logger = logging.getLogger(__name__)

@register_parser("midi")
class MidiParser(BaseParser):
    def __init__(self):
        try:
            import mido  # type: ignore
            self.mido = mido
        except Exception as exc:
            raise ImportError("mido required for MidiParser; pip install mido") from exc

    def parse(self, path: str) -> List[Event]:
        mid = self.mido.MidiFile(path)
        events: List[Event] = []
        ticks_per_beat = mid.ticks_per_beat or 480
        for track in mid.tracks:
            abs_ticks = 0
            tempo = 500000
            note_on = {}
            for msg in track:
                abs_ticks += msg.time
                time_s = self.mido.tick2second(abs_ticks, ticks_per_beat, tempo)
                if msg.type == "set_tempo":
                    tempo = msg.tempo
                    events.append(TempoEvent(start=time_s, bpm=60000000.0 / tempo))
                elif msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
                    note_on[(getattr(msg, "channel", 0), msg.note)] = time_s
                elif msg.type == "note_off" or (msg.type == "note_on" and getattr(msg, "velocity", 0) == 0):
                    key = (getattr(msg, "channel", 0), msg.note)
                    t0 = note_on.pop(key, None)
                    if t0 is not None:
                        duration = max(0.0, time_s - t0)
                        events.append(NoteEvent(start=t0, duration=duration, pitch=int(msg.note), velocity=getattr(msg, "velocity", 0), layer=f"midi_{getattr(msg, 'channel',0)}"))
        logger.debug("MIDI parsed: %d events", len(events))
        return events