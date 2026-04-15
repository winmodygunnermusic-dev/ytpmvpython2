# YTPMVPython

YTPMVPython is a modular Python toolkit for authoring YouTube Poop Music Videos (YTPMVs) by programmatically assembling audio and video from tracker modules, MIDI, and samples. It is designed for Windows-first workflows (8.1, 10, 11) while retaining cross-platform compatibility where possible.

Key goals
- Automate repetitive YTPMV workflow tasks while preserving creative control via Python code.
- Fast rendering using MoviePy (1.0.1) and OpenMPT-compatible module parsing (via CLI or bindings).
- Support tracker formats (.IT, .MOD, .XM, .S3M, .MPTM) plus MIDI.
- Scale to large/complex projects via chunked rendering, caching, and parallel processing.

This repository contains a modular implementation including parsers, a sample registry, chunked and parallel audio rendering, layered video compositing with effects, and a minimal preview GUI.

Features
- Parser plugin system (abstract base class) — easily add new input formats.
- MIDI parser (mido-based) and OpenMPT CLI adapter (JSON exporter expected).
- SampleRegistry for named sample mapping and lazy loading.
- Chunk-based audio rendering with optional file-based caching.
- Parallel chunk rendering using multiprocessing (ProcessPoolExecutor).
- Tempo-aware rendering and simple pitch-shifting (semitone-based resampling).
- VideoRenderer supporting layered compositing and visual effects (zoom, shake, color shift).
- Timeline utilities (chunking and batching) for efficient rendering of large projects.
- Minimal preview GUI (PySimpleGUI optional).
- Developer-friendly: type hints, docstrings, logging, example pipelines.

Requirements
- Python 3.8+
- moviepy==1.0.1
- numpy
- Optional:
  - mido (for MIDI parsing)
  - PySimpleGUI (for GUI preview)
  - An OpenMPT exporter CLI that outputs JSON event lists (or adapt the OpenMPT parser)
  - librosa, rubberband, or other DSP libraries for higher-quality pitch/time-stretching (not required)

Note: This project is Windows-first (tested on Windows 8.1/10/11) but uses cross-platform libraries when possible.

Quick install (recommended inside a virtualenv)
1. Create and activate a virtualenv:
   - python -m venv .venv
   - .venv\Scripts\activate  (Windows)
2. Install dependencies:
   - pip install moviepy==1.0.1 numpy
   - Optional: pip install mido PySimpleGUI

Project layout (important modules)
- ytpmpython/
  - events.py — Event model (Event, NoteEvent, TempoEvent) and helpers
  - parser/
    - base.py — BaseParser and parser registry
    - midi_parser.py — MIDI -> Event converter (mido)
    - openmpt_parser.py — OpenMPT CLI adapter (expects JSON)
  - samples/registry.py — SampleRegistry for named audio samples
  - utils/
    - cache.py — Simple file-based cache (FileCache)
    - timeline.py — chunk_timeline and batch_nearby_events helpers
  - renderer/
    - audio_renderer.py — Chunked, parallel audio renderer (caching, pitch/tempo)
    - video_renderer.py — Layered VideoRenderer and effect registry
  - gui/preview.py — Minimal timeline preview (PySimpleGUI optional)
  - logging_config.py — centralized logging setup
- examples/
  - basic_pipeline.py — basic end-to-end example
  - advanced_pipeline.py — OpenMPT example with batching and GUI preview
- README.md — this file

Usage examples

1) Basic pipeline (MIDI → samples → WAV/MP4)
- Ensure you have a MIDI file and example samples at `examples/data/` as referenced in `examples/basic_pipeline.py`.
- Run:
  - python examples/basic_pipeline.py
- What it does:
  - Parses MIDI (mido)
  - Registers sample files
  - Renders audio in chunked parallel workers and optionally caches chunks
  - Renders a simple video compositing image clips for a few note events

2) Advanced pipeline (OpenMPT → sample mapping → batching → GUI)
- Provide or adapt an OpenMPT JSON exporter and edit `ytpmpython/parser/openmpt_parser.py` OPENMPT_CMD to point to your tool (default `["openmpt_exporter", "--json"]`).
- Run:
  - python examples/advanced_pipeline.py
- What it does:
  - Parses module file using OpenMPT exporter (JSON)
  - Batches nearby events for smarter mixing
  - Renders audio with chunking and caching
  - Produces layered video with per-event effects
  - Launches a minimal preview GUI

Configuration notes

OpenMPT parser
- The bundled OpenMPT parser calls an external CLI exporter which must produce a JSON array of events where each event has:
  - type (e.g., "note", "tempo")
  - start (seconds)
  - duration (seconds)
  - meta (object with keys like pitch, velocity, sample, layer)
- If you do not have an OpenMPT JSON exporter, either:
  - Write a small wrapper that calls libopenmpt or the OpenMPT GUI to export events, or
  - Use the MIDI parser or write a parser plugin for your format.

Pitch shifting and time-stretching
- Current pitch shift is implemented by naive resampling (it changes duration). This is lightweight and works for many YTPMV effects.
- For higher-quality pitch shifting (preserving duration), integrate librosa (phase vocoder) or external tools (Rubber Band). If you want, I can add an optional librosa-based path.

Performance and scaling tips
- Use larger chunk_size to reduce process overhead when projects are large but scenes are long and memory allows.
- Tune max_workers to match CPU cores and I/O bandwidth.
- Use FileCache to persist chunk renders between runs and speed development iterations.
- Use `batch_nearby_events` to reduce redundant mixing work for closely spaced events.

Extending the parser system
- Create a new parser by subclassing BaseParser and decorating with `@register_parser("yourformat")`.
- Implement `parse(path: str) -> List[Event]`. Aim for streaming behavior on very large inputs.
- Parsers should output Event/NoteEvent/TempoEvent objects; `meta` can include custom keys (e.g., `base_note`, `sample`, `layer`, `visual`).

Effects system and visuals
- Visual effects are functions that accept a clip and return a transformed clip. Register effects or pass callables in event.meta['visual']['effects'].
- Add more effects by updating `_EFFECT_REGISTRY` in `ytpmpython/renderer/video_renderer.py` or by passing callables directly in your event metadata.

Developer experience
- The code includes type hints and docstrings for maintainability.
- Logging is centralized via `ytpmpython/logging_config.py`. Use `setup_logging(debug=True)` in examples.
- The code is modular — add new renderers, sample backends, or GUI elements as separate files.

Troubleshooting
- MoviePy writes temporary files during rendering; if runs fail, check for available disk space and permissions.
- On Windows, ensure ffmpeg is available in PATH (MoviePy uses ffmpeg). If ffmpeg is missing, install it and add to PATH.
- If MIDI parsing fails, install mido: `pip install mido`.
- If OpenMPT parsing fails, check `OPENMPT_CMD` and verify your exporter tool works on the command-line and outputs JSON.

Roadmap / TODO (suggested)
- Add optional librosa or Rubber Band support for high-quality pitch/time-stretch.
- Add a native timeline GUI (PySide6/Qt) for an editor-like experience with drag-and-drop sample assignment.
- Add unit tests and CI.
- Provide a packaged OpenMPT exporter wrapper for Windows (or documentation for configuring libopenmpt).
- Add a CLI and pyproject.toml for packaging and installation.

License
- MIT License — copy the contents of an MIT LICENSE file to the repo root (or change to your preferred license).

Contributing
- Send PRs with small, focused changes.
- Keep code modular and testable.
- Document new parser adapters and any added external dependencies.

Contact / Maintainers
- Project maintained in this repository. Please open issues or PRs for feature requests, bugs, or improvements.

Acknowledgements
- MoviePy (video/audio processing)
- numpy (audio arrays)
- mido (MIDI parsing; optional)
- OpenMPT / libopenmpt (module formats; external)

Example commands
- Run the basic example:
  - python examples/basic_pipeline.py
- Run the advanced example (after configuring OPENMPT_CMD and sample paths):
  - python examples/advanced_pipeline.py

If you'd like, I can:
- Add an MIT LICENSE file and a pyproject.toml for packaging.
- Provide a small OpenMPT->JSON exporter wrapper script targeted at Windows (PowerShell + libopenmpt binding) — tell me which OpenMPT tools you have.
- Replace naive pitch/time-stretch with librosa optionally and add reconcile code paths.
