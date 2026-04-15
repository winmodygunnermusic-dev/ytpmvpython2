# Running the YTPMVPython Editor (GUI) — Tutorial

This guide shows how to install dependencies, launch the YTPMVPython editor, open/save projects, assign samples to events, audition samples, and perform quick preview renders. It targets Windows (8.1/10/11) but also works on other platforms where the optional dependencies are available.

Prerequisites (quick)
- Python 3.8+
- ffmpeg on PATH (MoviePy requires ffmpeg)
- Clone or install the package:
  - From repo root: python -m venv .venv
  - Windows activate: .venv\Scripts\activate
  - Install core deps: pip install -e .[gui,midi] 
    - This installs moviepy, numpy and optional GUI/audio extras (PySimpleGUI, simpleaudio, mido).
  - Or install minimal: pip install -e .

Tip: If you prefer, install extras separately:
- pip install moviepy==1.0.1 numpy
- pip install PySimpleGUI simpleaudio mido

Files used by the tutorial
- ytpmpython/gui/editor.py — the GUI editor
- ytpmpython/gui/project.py — project save/load
- examples/basic_pipeline.py — example pipeline and how to open preview

1) Launch the editor (basic)
- From Python REPL or a simple script:
```python
from ytpmpython.gui.editor import run_editor
run_editor()  # opens an empty project editor
```
- Or run the example preview from the examples folder:
  - python examples/basic_pipeline.py
  - In the example, call `preview_timeline(events)` (the example may call it already).

2) Open an existing project (.ytpmv.json)
- In the Editor:
  - Click "Load" (or use the menu) and select a `.ytpmv.json` or `.json` file produced by the CLI or previous sessions.
- Programmatic:
```python
from ytpmpython.gui.project import Project
p = Project.load("my_project.ytpmv.json")
from ytpmpython.gui.editor import run_editor
run_editor(p)
```

3) Inspect the timeline and select events
- The left list shows events like `0.000s [0.500s] note | pitch=60, sample=vocal.wav`.
- Click any event to view/edit details on the right-hand panel (start, duration, sample, base_note, semitones, layer).

4) Assign a sample to an event
- With an event selected, click "Assign Sample".
- Browse to a WAV file (recommended WAV for simpleaudio playback) and confirm.
- The event's `meta['sample']` will be set to the file path and the project sample map is updated.

Drag & drop hint:
- You can drag a WAV from Explorer onto the window in many PySimpleGUI versions — it should assign the file to the currently selected event (behavior varies by environment).

5) Play the assigned sample (audition)
- With simpleaudio installed, click "Play Sample".
- If the sample is a WAV, the editor will use simpleaudio to play it (short, local audition).
- If simpleaudio is not installed or the file is not WAV, the button will be disabled or show a warning.

Install simpleaudio if you need audition:
- pip install simpleaudio

6) Edit tuning / mapping fields
- Base note: set the MIDI note number that corresponds to the sample's original pitch (useful for automatic pitch shifting).
- Semitones: direct semitone adjustment to apply to the sample when rendering.
- Layer: logical layer name (used by VideoRenderer to combine layers).

7) Save and export
- Click "Save" and pick a path like `my_project.ytpmv.json`.
- Use "Export Sample Map" to create a JSON mapping of sample logical names to file paths for use in other tools.

8) Quick preview / short render (recommended workflow)
- The project GUI includes a "Preview Timeline" button that either:
  - Launches a small listing preview (default), or
  - If your pipeline is wired, can call a preview callback that renders a short audio preview of the first N seconds.
- To add a quick-audio-preview button integration (developer):
  - Provide a function that takes a `Project` and calls `AudioRenderer.render()` for a short region (e.g., first 8–12 seconds) to a temp WAV, then play it with simpleaudio or open the file.

Example quick preview code (developer):
```python
from ytpmpython.renderer.audio import AudioRenderer
from ytpmpython.samples.registry import SampleRegistry
from ytpmpython.utils.cache import FileCache
import tempfile, simpleaudio as sa

def quick_preview(project):
    reg = SampleRegistry()
    for n,p in project.sample_map.items():
        reg.register(n, p)
    cache = FileCache(".preview_cache")
    ar = AudioRenderer(reg, cache=cache)
    events = project.events[:100]  # or crop by time
    out = tempfile.gettempdir() + "\\ytpmv_preview.wav"
    ar.render(events, out, chunk_size=6.0, tempo_bpm=project.meta.get("base_bpm", None), workers=1)
    # play
    wave_obj = sa.WaveObject.from_wave_file(out)
    play_obj = wave_obj.play()
    play_obj.wait_done()
```

9) Render full output from GUI (workflows)
- Workflow A (recommended):
  - Use the GUI to assemble and save a project (.ytpmv.json).
  - Run the CLI to render:
    - ytpmv render --project my_project.ytpmv.json --out out_video.mp4 --chunk 8.0 --workers 2
- Workflow B (developer-integrated):
  - Pass a preview callback `on_preview` to the Editor instance which triggers a render (be mindful of blocking UI; spawn a background thread for long jobs).

10) CLI quick commands
- Parse module into project:
  - ytpmv parse --format openmpt mymodule.it --out myproj.ytpmv.json
- Run a full conversion:
  - ytpmv run mymodule.it --out final.mp4 --chunk 8 --workers 2
- Render from a saved project:
  - ytpmv render --project myproj.ytpmv.json --out final.mp4

Windows tips
- Activate virtualenv before running GUI to ensure ffmpeg and Python deps are correct.
- If the GUI does not accept drag-and-drop: some Windows setups restrict file path forwarding between apps — use "Assign Sample" dialog as fallback.
- Ensure ffmpeg is in PATH (MoviePy needs it for video writing). Test with `ffmpeg -version`.

Troubleshooting
- GUI doesn't start / ImportError:
  - Check PySimpleGUI is installed in the environment used by Python.
- Play Sample fails:
  - Confirm simpleaudio installed and the file is WAV. Use another player to test the file.
- Rendering errors (ffmpeg / codec):
  - Install a build of ffmpeg that has libx264 and aac, and add its bin folder to PATH.
- OpenMPT parsing:
  - Set up an OpenMPT CLI exporter and modify `ytpmpython/parser/openmpt.py` OPENMPT_CLI_DEFAULT if necessary.

Developer notes (advanced)
- To wire a non-blocking preview in the editor, spawn the audio render in a background thread and update the GUI with progress messages.
- Add UI controls for:
  - Chunk size, tempo override, render workers, output resolution, and default visuals.
- For production-grade auditioning, integrate a streaming player or pre-generate short previews per event chunk.

Example end-to-end workflow (summary)
1. Install deps and ffmpeg.
2. Launch editor: python -c "from ytpmpython.gui.editor import run_editor; run_editor()"
3. Load or parse module to a project.
4. Assign samples to events and set base notes.
5. Save project.
6. In terminal: ytpmv render --project my_project.ytpmv.json --out final.mp4

If you'd like, I can:
- Add a "Quick Preview" button implementation that produces an in-GUI audio preview (non-blocking).
- Create a sample project and small example module + WAVs you can drop into `examples/data/`.
- Produce a packaged Windows installer or a ready-to-run ZIP with ffmpeg and a small OpenMPT->JSON exporter.

Which of those would help you next?