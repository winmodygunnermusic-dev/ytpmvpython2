"""
Project model for saving/loading timelines + sample maps.
"""

from typing import Any, Dict, List, Optional
import json
from ..events import Event, NoteEvent, TempoEvent
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)

def _evt_to_dict(e: Event) -> Dict[str, Any]:
    return {"start": float(e.start), "duration": float(e.duration), "type": e.type, "meta": e.meta or {}}

def _evt_from(d: Dict[str, Any]) -> Event:
    t = d.get("type", "event")
    s = float(d.get("start", 0.0))
    dur = float(d.get("duration", 0.0))
    meta = d.get("meta", {}) or {}
    if t == "note":
        try:
            return NoteEvent(start=s, duration=dur, pitch=int(meta.get("pitch", 60)), velocity=int(meta.get("velocity", 100)), sample=meta.get("sample"), layer=meta.get("layer"), **{k: v for k, v in meta.items() if k not in ("pitch","velocity","sample","layer")})
        except Exception:
            pass
    if t == "tempo":
        return TempoEvent(start=s, bpm=float(meta.get("bpm", 120.0)))
    return Event(start=s, duration=dur, type=t, meta=meta)

class Project:
    def __init__(self, events: Optional[List[Event]] = None, sample_map: Optional[Dict[str,str]] = None, meta: Optional[Dict[str,Any]] = None):
        self.events = events or []
        self.sample_map = sample_map or {}
        self.meta = meta or {"version": "2.0"}

    def to_dict(self):
        return {"meta": self.meta, "sample_map": self.sample_map, "events": [_evt_to_dict(e) for e in self.events]}

    @classmethod
    def from_dict(cls, data):
        events = [_evt_from(e) for e in data.get("events", [])]
        return cls(events=events, sample_map=data.get("sample_map", {}), meta=data.get("meta", {}))

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
        logger.info("Project saved: %s", path)

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        p = cls.from_dict(data)
        logger.info("Project loaded: %s", path)
        return p