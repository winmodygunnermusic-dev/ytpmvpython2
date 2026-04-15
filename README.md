# YTPMVPython v2

YTPMVPython v2 is a modular toolkit that converts tracker modules (OpenMPT-compatible formats) and MIDI into YTPMV videos using a code-driven pipeline. It focuses on chunked, parallel audio rendering, tempo-aware processing, pitch shifting, layered video compositing, caching, and a lightweight editor.

Quick start
1. Ensure Python 3.8+, ffmpeg on PATH.
2. Install: pip install -e .[gui,midi]
3. Run CLI: ytpmv --help

Core features
- Parser plugin system (OpenMPT CLI/libopenmpt + MIDI)
- Chunked, parallel audio renderer with caching
- Video renderer with layered compositing and effects
- Project JSON save/load
- Minimal PySimpleGUI editor for sample assignment and preview
- CLI entrypoint to convert module -> project -> render

See examples/ for usage demos.