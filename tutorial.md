# YTPMVPython — Tutorial

This tutorial walks you through installing, running, and extending YTPMVPython. It covers the common workflows (basic MIDI → samples → audio/video), the advanced OpenMPT workflow, tuning performance for large projects (chunking, caching, parallelism), and how to add parsers, effects, and custom visuals. Follow the Quick Start section first, then read the Deep Dive sections to customize behavior for production-sized YTPMVs.

Table of contents
- Quick prerequisites
- Quick start (basic pipeline)
- Advanced: OpenMPT workflow
- Rendering internals (chunking, caching, parallel rendering)
- Tempo, pitch, and audio quality tips
- Video effects and layered compositing
- Extending the parser system (plugin example)
- Extending effects (example)
- GUI preview usage
- Troubleshooting and common errors
- Next steps and recommended improvements

--------------------------
Quick prerequisites
--------------------------

- Python 3.8+ (3.8, 3.9, 3.10, 3.11 should work)
- moviepy==1.0.1
- numpy
- ffmpeg installed and on your PATH (MoviePy uses ffmpeg)
- Optional:
  - mido (for MIDI parsing): pip install mido
  - PySimpleGUI (for preview GUI): pip install PySimpleGUI
  - An OpenMPT exporter CLI (optional; used by openmpt_parser)

Windows quick setup (recommended)
1. Create and activate a venv:
   - python -m venv .venv
   - .venv\Scripts\activate
2. Install core deps:
   - pip install moviepy==1.0.1 numpy
3. Optional:
   - pip install mido PySimpleGUI
4. Ensure ffmpeg is installed and available on PATH:
   - Download ffmpeg from https://ffmpeg.org and add the `bin` folder to PATH.

--------------------------
Quick start — basic example
--------------------------

1. Prepare files
   - Put a MIDI file at `examples/data/example.mid`.
   - Place a couple of WAV samples at `examples/data/samples/`:
     - piano_A.wav
     - vocal_hit.wav
   - Add a placeholder image `examples/data/samples/placeholder.png`.

2. Run the basic pipeline:
   - From repo root:
     - python examples/basic_pipeline.py

What it does (summary)
- The MIDI parser (mido-based) converts note events to Event objects.
- A SampleRegistry is used to map sample names to WAV files.
- AudioRenderer splits the timeline into chunks and renders them in parallel, writing `out/basic_audio.wav`.
- VideoRenderer creates a simple layered video using the placeholder image and writes `out/basic_video.mp4`.

Important API notes (basic)
- The core objects you will use
  - Event / NoteEvent / TempoEvent (ytpmpython/events.py)
  - get_parser_for_format(format_name) to get parser instances (ytpmpython/parser/base.py)
  - SampleRegistry to register and obtain sample paths/clips (ytpmpython/samples/registry.py)
  - AudioRenderer and VideoRenderer for rendering (ytpmpython/renderer/)

Example: rendering audio programmatically

```python
from ytpmpython.samples.registry import SampleRegistry
from ytpmpython.renderer.audio_renderer import AudioRenderer
from ytpmpython.utils.cache import FileCache

reg = SampleRegistry()
reg.register("piano_A", "examples/data/samples/piano_A.wav")
audio_renderer = AudioRenderer(reg, cache=FileCache(".cache"), sample_rate=44100)
audio_renderer.render(events, "out/my_audio.wav", chunk_size=8.0, tempo_bpm=120.0, max_workers=2)
```

--------------------------
Advanced: OpenMPT workflow
--------------------------

The OpenMPT parser is an adapter that expects a CLI exporter to produce JSON event arrays. By default the parser calls:

OPENMPT_CMD = ["openmpt_exporter", "--json"]

If you have a command-line exporter that outputs event JSON, set or modify OPENMPT_CMD in `ytpmpython/parser/openmpt_parser.py` to match your tool.

Run the advanced example:
- python examples/advanced_pipeline.py

This script demonstrates:
- Calling the OpenMPT exporter to read tracker modules
- Batching nearby events for smarter mixing
- Chunked audio rendering with caching and faster re-runs
- Layered visuals with per-event effects
- Minimal GUI preview

If you don't have an OpenMPT exporter, use the MIDI parser or write a small wrapper around libopenmpt to emit compatible JSON.

--------------------------
Rendering internals — chunking, batching, caching
--------------------------

Why chunking?
- Long timelines (minutes/hours) become heavy to mix in memory.
- Chunking splits the timeline into time windows so each process only mixes a small portion.
- Overlapping events are included in both chunks and clipped on output, so artists can use short overlap margins for smooth transitions.

Key helpers
- chunk_timeline(events, chunk_size) -> list of (chunk_start, chunk_end, events_in_chunk)
- batch_nearby_events(events, proximity) -> groups events that are close in time

AudioRenderer strategy (summary)
- Prepare chunk tasks with a deterministic hash key based on events and parameters.
- If a FileCache is provided, attempt to read cached rendered chunk bytes.
- Render chunks in a ProcessPoolExecutor to avoid GIL contention.
- Each worker writes a temporary WAV, main process reads and concatenates clips with MoviePy.
- Temporally overlapping events included in multiple chunks are clipped by chunk boundaries.

Tuning guidelines
- chunk_size:
  - Small (2–8s) → faster incremental re-renders, more process overhead and more temporary files.
  - Large (10–30s) → lower overhead but more memory per worker.
- max_workers:
  - Usually 2–4 on a typical Windows dev machine. Match to CPU cores and disk I/O.
- cache_age:
  - Keep cached chunks around to speed iterative development. Purge or bump cache keys when you change render logic.

--------------------------
Tempo, pitch, and audio quality tips
--------------------------

Current implementation notes
- Tempo-aware rendering: `AudioRenderer.render(..., tempo_bpm=...)` scales sample playback speed (simple speed change).
- Pitch shifting:
  - Implemented using naive resampling (changes duration).
  - If you need pitch shift without duration change, integrate a phase vocoder (librosa) or an external tool (Rubber Band).
- For high-quality production sound:
  - Install librosa and add an optional path that uses `librosa.effects.pitch_shift` + `librosa.effects.time_stretch`.
  - Consider using dedicated tools (sox, rubberband) for time-stretch/pitch preservation.

Example: optional librosa-based pitch shift (concept)
```python
import librosa
y, sr = librosa.load(sample_path, sr=target_sr)
y_shifted = librosa.effects.pitch_shift(y, sr, n_steps=semitones)
# convert mono->stereo and then return numpy array used by AudioArrayClip
```

--------------------------
Video effects and layered compositing
--------------------------

VideoRenderer features
- Background ColorClip for base
- Each Event may provide `meta['visual']` with:
  - 'image' or 'video' keys (file path)
  - 'effects': list of names or callables
  - 'opacity', 'position', etc.
- Effects are callables accepting a clip and returning a modified clip. The repo ships with:
  - zoom, shake, color_shift

Adding or customizing effects
- Either register your effect in the _EFFECT_REGISTRY in `video_renderer.py` or pass callables directly:
```python
def my_glitch(clip):
    # return modified clip
    return clip.fx(...)

e.meta['visual']['effects'] = [my_glitch, "zoom"]
```

Layering tips
- Use `e.meta['layer']` to logically group events. VideoRenderer places all clips into a CompositeVideoClip; ordering of list affects z-order.
- Use smaller image/video sizes for speed; scale in the clip pipeline when necessary.

--------------------------
Extending the parser system (plugin example)
--------------------------

Create a new parser plugin by subclassing `BaseParser` and using the register_parser decorator.

Example: minimal "simplejson" parser that reads an array of events:

```python
# ytpmpython/parser/simplejson_parser.py
from .base import register_parser, BaseParser
from typing import List
from ..events import Event, NoteEvent, TempoEvent
import json

@register_parser("simplejson")
class SimpleJsonParser(BaseParser):
    def parse(self, path: str) -> List[Event]:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        events = []
        for it in data:
            t = it.get("type", "note")
            s = float(it.get("start", 0.0))
            d = float(it.get("duration", 0.0))
            meta = it.get("meta", {})
            if t == "note":
                events.append(NoteEvent(start=s, duration=d, pitch=int(meta.get("pitch", 60)), velocity=int(meta.get("velocity", 100)), sample=meta.get("sample"), layer=meta.get("layer")))
            elif t == "tempo":
                events.append(TempoEvent(start=s, bpm=float(meta.get("bpm", 120.0))))
            else:
                events.append(Event(start=s, duration=d, type=t, meta=meta))
        return events
```

Then use:
```python
from ytpmpython.parser.base import get_parser_for_format
p = get_parser_for_format("simplejson")
events = p.parse("my_events.json")
```

Best practices
- Keep `parse` memory-efficient: stream large files instead of loading huge structures when possible.
- Return Event / NoteEvent / TempoEvent objects to ensure renderer compatibility.
- Use `meta` for format-specific keys like `base_note`, `sample`, `visual` etc.

--------------------------
Extending effects (example)
--------------------------

Example effect that tints a clip blue:

```python
from moviepy.video.fx.all import colorx
def blue_tint(clip):
    # colorx multiplies color channels; this is very simple
    return clip.fl_image(lambda frame: (frame * np.array([0.6, 0.9, 1.2])).clip(0,255).astype('uint8'))
```

Add to registry (in video_renderer.py or at runtime):

```python
from ytpmpython.renderer.video_renderer import _EFFECT_REGISTRY
_EFFECT_REGISTRY["blue_tint"] = blue_tint
```

Then in event metadata:
```python
e.meta['visual'] = {'image': 'path.png', 'effects': ['blue_tint', 'zoom']}
```

--------------------------
GUI preview usage
--------------------------

The GUI preview is a minimal helper for quick checks and sample assignment:
- Requires PySimpleGUI (optional).
- Launches `preview_timeline(events)` which opens a window listing events and basic action buttons.

Drag-and-drop sample assignment is not implemented as a fully-featured editor; instead, use the preview to inspect events then programmatically modify `e.meta['sample']` and re-run the pipeline.

For a full editor consider using PySide6/Qt for a native timeline and drag/drop.

--------------------------
Troubleshooting and common errors
--------------------------

1. MoviePy / ffmpeg errors
   - Ensure ffmpeg binary is installed and on PATH.
   - If MoviePy complains about missing codecs, install ffmpeg and verify video writers (libx264, aac) are available.

2. MIDI parsing errors
   - Install mido: pip install mido

3. OpenMPT parsing errors
   - Make sure `OPENMPT_CMD` is correct for your environment and that the exporter returns valid JSON to stdout.
   - Run the exporter manually to check output: openmpt_exporter --json example.it

4. Chunk render failures / worker exceptions
   - Inspect logs; set debug True via `setup_logging(debug=True)` and `AudioRenderer(debug=True)`.
   - Ensure sample paths exist and are readable.

5. Audio clipping or silence
   - Ensure sample files are normalized. Audio mixing sums signals — normalization is applied per chunk but you may need to adjust levels.

6. Temporary file cleanup
   - Temporary WAV files are written to the system temp folder and removed after concatenation. If a process fails mid-run, temporary files may remain; it's safe to delete them.

--------------------------
Next steps / recommended improvements
--------------------------

If you want to make this production-ready for large YTPMVs, consider:
- High-quality pitch/time-stretch with librosa or Rubber Band.
- A native timeline GUI (PySide6) with real-time scrub, drag & drop, and track lanes.
- Unit tests around chunking, caching, and parser adapters.
- A CLI entrypoint and packaging (pyproject.toml + setuptools/poetry).
- A robust OpenMPT exporter wrapper for Windows that uses libopenmpt to produce JSON events.

--------------------------
Appendix: API quick reference
--------------------------

- Events
  - Event(start: float, duration: float, type: str, meta: dict)
  - NoteEvent(start, duration, pitch, velocity, sample, layer)
  - TempoEvent(start, bpm)

- Parsers
  - from ytpmpython.parser.base import get_parser_for_format
  - p = get_parser_for_format("midi")  # or "openmpt"

- Sample registry
  - from ytpmpython.samples.registry import SampleRegistry
  - reg = SampleRegistry(); reg.register("name", "path.wav")

- Audio rendering
  - from ytpmpython.renderer.audio_renderer import AudioRenderer
  - ar = AudioRenderer(reg, cache=FileCache(".cache"), sample_rate=44100)
  - ar.render(events, "out.wav", chunk_size=8.0, tempo_bpm=120.0, max_workers=2)

- Video rendering
  - from ytpmpython.renderer.video_renderer import VideoRenderer
  - vr = VideoRenderer(duration=total_duration, bg_color=(0,0,0))
  - vr.render(events, audio_path="out.wav", out_path="out.mp4", default_image="placeholder.png", fps=24)

--------------------------
Wrap-up
--------------------------

This tutorial should get you started producing YTPMVs with programmatic control over timeline, samples, and visuals. Use the examples as a foundation and extend parsers, effects, and GUI pieces as your project grows. If you'd like, I can:
- Add a step-by-step recorded example (screencast-style instructions)
- Implement librosa-based pitch/time-stretch fallback
- Provide a packaged CLI and pyproject.toml for easier installation

Tell me which of those you'd like next and I will add it.