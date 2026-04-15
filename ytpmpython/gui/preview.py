"""
Preview launcher updated to use the interactive Editor when available.

This module preserves the previous simple preview behavior when PySimpleGUI is
not installed, but will launch the richer Editor if PySimpleGUI is present.
"""

from typing import List
from ..events import Event
import logging

logger = logging.getLogger(__name__)

try:
    from .editor import Editor  # type: ignore
    from .project import Project  # type: ignore
    HAS_EDITOR = True
except Exception:
    HAS_EDITOR = False

def preview_timeline(events: List[Event]):
    """
    Open an interactive editor if available, otherwise log/print a simple timeline listing.
    """
    if HAS_EDITOR:
        # Create a temporary project and launch Editor
        proj = Project.from_events(events, sample_map={})
        ed = Editor(project=proj)
        ed.run()
    else:
        # Fallback
        logger.info("Interactive editor not available; printing timeline:")
        for e in events:
            logger.info("Event: start=%.3f dur=%.3f type=%s meta=%r", e.start, e.duration, e.type, e.meta)