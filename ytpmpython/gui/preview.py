"""
Simple preview GUI for timeline and sample assignment.

This is a minimal Windows-first GUI using PySimpleGUI if available. The goal
is not a full DAW but a compact preview tool for quick testing and drag-drop
assignment in the project.

If PySimpleGUI is not installed, the module falls back to a CLI preview.
"""

import logging
from typing import List
from ..events import Event
import webbrowser

logger = logging.getLogger(__name__)

try:
    import PySimpleGUI as sg  # type: ignore
    HAS_PYSIMPLEGUI = True
except Exception:
    HAS_PYSIMPLEGUI = False

def preview_timeline(events: List[Event]):
    """
    Launch a minimal preview window listing events and offering to open generated files.
    """
    if HAS_PYSIMPLEGUI:
        layout = [
            [sg.Text("YTPMV Timeline Preview")],
            [sg.Listbox(values=[f"{e.start:.2f}s {e.type} {e.meta}" for e in events], size=(80, 20))],
            [sg.Button("Open Output Folder"), sg.Button("Close")],
        ]
        window = sg.Window("YTPMV Preview", layout, finalize=True)
        while True:
            event, values = window.read()
            if event in (None, "Close"):
                break
            if event == "Open Output Folder":
                webbrowser.open(".")
        window.close()
    else:
        logger.info("PySimpleGUI not installed — CLI preview:")
        for e in events:
            logger.info("Event: start=%.3f dur=%.3f type=%s meta=%r", e.start, e.duration, e.type, e.meta)