# Running YTPMVPython (v2) — Quick Reference

This document explains how to run YTPMVPython v2 on Windows (recommended) and other platforms. It includes installation, CLI usage, GUI/editor usage, example pipelines, tips for performance and troubleshooting, and common workflows (parse → edit → render).

Table of Contents
- Prerequisites
- Install (dev / editable)
- Verify environment
- Quick CLI examples
- Full run: parse → edit → render
- GUI/editor quick guide
- Quick preview (audio)
- Performance tuning and troubleshooting
- Advanced: OpenMPT / MIDI tips
- Scripts & automation
- Next steps

Prerequisites
- Python 3.8+ (3.8 — 3.11 tested)
- ffmpeg available on PATH (MoviePy requires ffmpeg)
- Install core Python deps:
  - moviepy==1.0.1
  - numpy
- Optional useful packages:
  - mido (MIDI parsing)
  - PySimpleGUI (GUI editor)
  - simpleaudio (preview playback)
  - librosa + soundfile (high-quality pitch/time-stretch)
- On Windows: prefer using a virtualenv for isolation.

Install (editable / dev)
1. Create and activate a virtualenv (Windows):
   - python -m venv .venv
   - .venv\Scripts\activate
2. From repo root (where pyproject.toml is located):
   - pip install -e .[gui,midi]    # installs optional GUI/midi extras
   - or for minimal: pip install -e .

Verify environment
- ffmpeg: open terminal, run:
  - ffmpeg -version
  If not found, download ffmpeg and add its bin folder to PATH.
- Python deps: inside venv:
  - python -c "import moviepy, numpy; print(moviepy.__version__, numpy.__version__)"

Quick CLI examples
The package installs the `ytpmv` console script.

1) Show help:
   - ytpmv --help

2) Parse a module to a project (OpenMPT or MIDI):
   - ytpmv parse --format openmpt input.it --out myproj.ytpmv.json
   - ytpmv parse --format midi input.mid --out myproj.ytpmv.json

3) Render from a saved project:
   - ytpmv render --project myproj.ytpmv.json --out final.mp4 --chunk 8.0 --workers 2 --fps 24 --width 1280 --height 720

4) One-step run (auto-detect format if not supplied):
   - ytpmv run input.it --out final.mp4 --chunk 8.0 --workers 2

Common CLI flags (defaults shown in examples)
- --chunk N         : chunk size in seconds for chunked rendering (default ~8.0)
- --workers N       : ProcessPoolWorker count for audio chunk rendering (default ~2)
- --tempo BPM       : optional tempo override (tempo-aware rendering)
- --fps N, --width, --height : video resolution & framerate

Full pipeline (parse → edit → render)
1. Parse:
   - ytpmv parse --format openmpt mymodule.it --out project.ytpmv.json
   - (MIDI: --format midi)
2. Edit in GUI (assign samples, tune base_note, semitones):
   - Use the editor: in Python REPL or script:
     - from ytpmpython.gui.editor import run_editor
     - run_editor(Project.load("project.ytpmv.json"))
   - Or open the editor via examples that call preview_timeline()
3. Render:
   - ytpmv render --project project.ytpmv.json --out final.mp4

GUI / Editor quick guide
- Start an editor session:
  - run_editor() or run the example that calls preview_timeline().
- Main features:
  - Load / Save project (.ytpmv.json)
  - Select events from timeline list
  - Assign sample file (WAV recommended) to selected event
  - Set base_note (MIDI) for pitch-aware rendering
  - Set semitones for manual pitch adjustment
  - Play Sample (requires simpleaudio and WAV)
  - Export sample map (JSON)
  - Preview Timeline → opens a quick listing or the preview callback (if configured)

GUI tips (Windows)
- Drag-and-drop WAV files may work in some environments — use "Assign Sample" if not.
- Use WAV for simple auditioning with simpleaudio.
- For blocking heavy operations (render), run the render from a terminal, not from the GUI main thread.

Quick preview (short audio preview)
- The editor can be extended to call the AudioRenderer for a short preview:
  - Render the first N seconds using AudioRenderer (chunk_size 4–8s, workers 1)
  - Play the resulting WAV with simpleaudio
- Developer sample snippet (non-blocking recommended — spawn thread):

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
      # Render only events within first 8 seconds
      events = [e for e in project.events if e.start < 8.0]
      out = tempfile.gettempdir() + "\\ytpmv_preview.wav"
      ar.render(events, out, chunk_size=6.0, tempo_bpm=project.meta.get("base_bpm", None), workers=1)
      wave_obj = sa.WaveObject.from_wave_file(out)
      play_obj = wave_obj.play()
      play_obj.wait_done()

Performance tuning & troubleshooting
- Chunk size:
  - Smaller (2–6s): faster iteration, higher overhead and many temporary files.
  - Larger (10–30s): fewer tasks and less overhead but higher per-worker memory use.
- max_workers:
  - Use 2–4 workers on typical dev machines; increase if CPU & disk can handle it.
- FileCache:
  - Reuse cached chunk outputs to speed iterative work. Clear cache after major logic changes.
- Disk/Temp files:
  - Chunk rendering writes temp WAVs. Ensure temp folder has space and permission to remove files.
- MoviePy / ffmpeg errors:
  - Ensure ffmpeg binary is installed and supports required codecs (libx264, aac).
- Silent output or clipping:
  - Verify sample paths and sample levels. The renderer normalizes per-chunk but large mixed values can still clip.
- Worker crashes:
  - Check logs (set debug logging) and sample file validity. Try single-worker to collect full trace.

Advanced: OpenMPT & MIDI notes
- OpenMPT:
  - The OpenMPT parser expects a JSON exporter CLI (default `openmpt_exporter --json`) or a python binding (libopenmpt), which may vary by system.
  - If you have a specific exporter, update `ytpmpython/parser/openmpt.py` OPENMPT_CLI_DEFAULT to your command.
  - Test the exporter manually first: openmpt_exporter --json mymodule.it
- MIDI:
  - Install mido (`pip install mido`) for MIDI parsing.
  - The MIDI parser uses mido tick->seconds conversion and emits tempo events when present.

Upgrading audio quality (optional)
- Naive pitch shifting uses resampling (changes duration).
- For high-quality pitch shift without duration change, install `librosa` and `soundfile` and update the audio renderer to use `librosa.effects.pitch_shift` and `librosa.effects.time_stretch`.
- External tools (Rubber Band) provide production-grade time-stretching and pitch-shifting.

Automation & batch scripting
- Use CLI in build scripts or CI to render batches:
  - ytpmv run module.it --out out.mp4 --chunk 8 --workers 3
- For many modules, script a loop in PowerShell / CMD to parse and render automatically.

Common commands cheat-sheet
- Parse: ytpmv parse --format openmpt input.it --out project.json
- Render: ytpmv render --project project.json --out final.mp4 --chunk 8 --workers 2
- One-step run: ytpmv run input.it --out final.mp4

Common issues & resolutions
- "ffmpeg not found" → add ffmpeg bin to PATH.
- "OpenMPT exporter not found" → install or configure exporter CLI and update parser CLI constant.
- "simpleaudio playback fails" → ensure WAV files and simpleaudio installed; use another player to test the file.
- "Large memory or slow runs" → increase chunking, reduce workers, or use faster disk.

Example end-to-end (Windows)
1. Setup:
   - python -m venv .venv
   - .venv\Scripts\activate
   - pip install -e .[gui,midi]
   - Ensure ffmpeg in PATH
2. Parse:
   - ytpmv parse --format openmpt song.it --out song.ytpmv.json
3. Edit (assign samples):
   - python -c "from ytpmpython.gui.editor import run_editor; run_editor()"
   - Load song.ytpmv.json, assign samples and save
4. Render:
   - ytpmv render --project song.ytpmv.json --out song.mp4 --chunk 8 --workers 2

Next steps and customization ideas
- Add an optional high-quality audio backend using librosa.
- Provide a packaged Windows bundle with ffmpeg and an OpenMPT->JSON helper CLI.
- Build a native timeline GUI (PySide6) for non-blocking renders and more advanced editing.
- Add unit tests for chunking, caching, and parser adapters.

If you want, I can:
- Add a non-blocking "Quick Preview" button to the Editor that renders and plays a short preview.
- Provide a ready-to-run example module and set of WAV samples under `examples/data/`.
- Create a Windows-friendly OpenMPT->JSON exporter script (PowerShell + libopenmpt wrapper).
Which of the above would you like next?