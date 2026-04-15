"""
OpenMPT parser adapter.

Strategy:
- If python binding for libopenmpt is available (pyopenmpt / libopenmpt), use it.
- Else, call an external CLI exporter which should output JSON events (configurable).
"""

from typing import List
from ..events import Event, NoteEvent, TempoEvent
from .base import register_parser, BaseParser
import logging
import json
import subprocess
import shutil

logger = logging.getLogger(__name__)

# Default external exporter (adjust to your environment)
OPENMPT_CLI_DEFAULT = ["openmpt_exporter", "--json"]

@register_parser("openmpt")
class OpenMPTParser(BaseParser):
    def __init__(self, cli_cmd: List[str] | None = None):
        self.cli_cmd = cli_cmd or OPENMPT_CLI_DEFAULT
        # detect if libopenmpt python binding exists (best-effort)
        try:
            import openmpt  # type: ignore
            self._has_binding = True
        except Exception:
            self._has_binding = False

    def parse(self, path: str) -> List[Event]:
        if self._has_binding:
            try:
                # Example pseudo-usage: many bindings differ; provide a graceful message
                import openmpt  # type: ignore
                logger.debug("libopenmpt binding present but using CLI fallback for portability.")
                # Most users will rely on CLI; implement binding-specific logic when you have a tested binding.
            except Exception:
                pass
        # Fallback: CLI exporter
        if not shutil.which(self.cli_cmd[0]):
            raise RuntimeError(f"OpenMPT exporter CLI '{self.cli_cmd[0]}' not found. Install or adjust parser configuration.")
        cmd = self.cli_cmd + [path]
        logger.debug("Running OpenMPT CLI: %s", cmd)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            logger.error("OpenMPT exporter failed: %s", proc.stderr.decode(errors="ignore"))
            raise RuntimeError("OpenMPT exporter failed; inspect CLI output.")
        try:
            data = json.loads(proc.stdout.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Failed to parse JSON from OpenMPT exporter") from exc
        events: List[Event] = []
        for it in data:
            t = it.get("type", "note")
            start = float(it.get("start", 0.0))
            duration = float(it.get("duration", 0.0))
            meta = it.get("meta", {}) or {}
            if t == "note":
                pitch = int(meta.get("pitch", 60))
                vel = int(meta.get("velocity", 100))
                events.append(NoteEvent(start=start, duration=duration, pitch=pitch, velocity=vel, sample=meta.get("sample"), layer=meta.get("layer")))
            elif t == "tempo":
                events.append(TempoEvent(start=start, bpm=float(meta.get("bpm", 120.0))))
            else:
                events.append(Event(start=start, duration=duration, type=t, meta=meta))
        logger.debug("OpenMPT parsed: %d events", len(events))
        return events