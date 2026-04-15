"""
OpenMPT CLI adapter parser.

This parser expects an external CLI tool that can export module event data as JSON.
The exact tool is left to the user; by default it calls `openmpt_exporter --json {path}`.
Adjust OPENMPT_CMD as needed for your environment.

The JSON must be a list of events with fields:
  - type: "note" | "tempo" | ...
  - start: seconds
  - duration: seconds
  - meta: dict
"""

from typing import List
from ..events import Event, NoteEvent, TempoEvent
from .base import register_parser, BaseParser
import json
import subprocess
import logging

logger = logging.getLogger(__name__)

OPENMPT_CMD = ["openmpt_exporter", "--json"]  # User must provide/adjust this CLI

@register_parser("openmpt")
class OpenMPTParser(BaseParser):
    """
    Parser that calls an OpenMPT exporter CLI which writes JSON event lists to stdout.

    This class is a small adapter; you must install or provide `openmpt_exporter` or
    change OPENMPT_CMD to the proper binary.
    """

    def parse(self, path: str) -> List[Event]:
        cmd = OPENMPT_CMD + [path]
        logger.debug("Running OpenMPT exporter: %s", cmd)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            logger.error("OpenMPT exporter failed: %s", proc.stderr.decode(errors="ignore"))
            raise RuntimeError("OpenMPT exporter failed; check OPENMPT_CMD and availability.")
        try:
            data = json.loads(proc.stdout.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Failed to parse OpenMPT exporter JSON output.") from exc
        events: List[Event] = []
        for item in data:
            t = item.get("type")
            start = float(item.get("start", 0.0))
            duration = float(item.get("duration", 0.0))
            meta = item.get("meta", {})
            if t == "note":
                events.append(NoteEvent(start=start, duration=duration,
                                        pitch=int(meta.get("pitch", 60)),
                                        velocity=int(meta.get("velocity", 100)),
                                        sample=meta.get("sample"), layer=meta.get("layer")))
            elif t == "tempo":
                events.append(TempoEvent(start=start, bpm=float(meta.get("bpm", 120.0))))
            else:
                events.append(Event(start=start, duration=duration, type=t, meta=meta))
        logger.debug("Parsed %d events from OpenMPT JSON", len(events))
        return events