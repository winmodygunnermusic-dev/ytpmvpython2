"""
Lightweight PySimpleGUI-based editor for sample assignment and project save/load.

Optional: install PySimpleGUI and simpleaudio for playback.
"""

from typing import Optional
from .project import Project
from ..events import Event
import logging
import os

logger = logging.getLogger(__name__)

try:
    import PySimpleGUI as sg  # type: ignore
    HAS_GUI = True
except Exception:
    HAS_GUI = False

try:
    import simpleaudio as sa  # type: ignore
    HAS_SA = True
except Exception:
    HAS_SA = False

def run_editor(project: Optional[Project] = None):
    project = project or Project()
    if not HAS_GUI:
        logger.info("PySimpleGUI not installed. CLI fallback:")
        for i, e in enumerate(project.events):
            logger.info("[%d] %s (meta=%s)", i, e, e.meta)
        return
    sg.theme("DarkBlue3")
    layout = [
        [sg.Text("YTPMV Editor v2")],
        [sg.Listbox(values=[f"{e.start:.2f}s {e.type} {e.meta}" for e in project.events], size=(80,20), key="-LIST-", enable_events=True)],
        [sg.Button("Load"), sg.Button("Save"), sg.Button("Assign Sample"), sg.Button("Exit")]
    ]
    window = sg.Window("YTPMVPython Editor", layout, finalize=True)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit", None):
            break
        if event == "Load":
            p = sg.popup_get_file("Open project", file_types=(("json","*.json"),("ytpmv","*.ytpmv.json"),("All","*.*")))
            if p:
                try:
                    project = Project.load(p)
                    window["-LIST-"].update(values=[f"{e.start:.2f}s {e.type} {e.meta}" for e in project.events])
                except Exception as exc:
                    sg.popup("Load failed", str(exc))
        if event == "Save":
            p = sg.popup_get_file("Save project", save_as=True, file_types=(("ytpmv","*.ytpmv.json"),("json","*.json")))
            if p:
                try:
                    project.save(p)
                    sg.popup("Saved")
                except Exception as exc:
                    sg.popup("Save failed", str(exc))
        if event == "Assign Sample":
            sel = values.get("-LIST-")
            if not sel:
                sg.popup("Select an event first")
                continue
            idx = values["-LIST-"].index(sel[0])
            f = sg.popup_get_file("Choose sample", file_types=(("wav","*.wav"),("all","*.*")))
            if f:
                project.events[idx].meta["sample"] = f
                window["-LIST-"].update(values=[f"{e.start:.2f}s {e.type} {e.meta}" for e in project.events])
    window.close()