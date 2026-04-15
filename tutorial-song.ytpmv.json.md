name=tutorial-song.ytpmv.json.md
# Tutorial: example project file — tutorial-song.ytpmv.json

This document shows a complete example project (JSON) you can use with YTPMVPython v2. Save the JSON block below as `tutorial-song.ytpmv.json` (or copy to your editor) and then:

- Open it in the Editor (File → Load) to inspect and assign/override samples and visuals.
- Or render from the CLI:

```bash
ytpmv render --project tutorial-song.ytpmv.json --out tutorial-song.mp4 --chunk 8 --workers 2
```

(That CLI invocation will render audio then compose the video — adjust chunk size and workers to suit your machine.)

Example JSON project
- `metadata` holds project-level info (title, author, base_bpm).
- `sample_map` maps logical sample names to file paths (relative or absolute).
- `events` is an array of timeline events. Each event has:
  - `start` (seconds), `duration` (seconds)
  - `type` ("note", "tempo", or other)
  - `meta` (custom keys: pitch, velocity, sample, base_note, semitones, layer, visual, etc.)

Copy and save the following JSON as `tutorial-song.ytpmv.json`:

```json
{
  "meta": {
    "title": "Tutorial Song",
    "author": "YTPMVPython Example",
    "base_bpm": 140,
    "version": "2.0"
  },
  "sample_map": {
    "vocal_hit": "examples/data/samples/vocal_hit.wav",
    "piano_A": "examples/data/samples/piano_A.wav",
    "bass_loop": "examples/data/samples/bass_loop.wav",
    "placeholder_img": "examples/data/samples/placeholder.png"
  },
  "events": [
    {
      "start": 0.0,
      "duration": 0.0,
      "type": "tempo",
      "meta": {
        "bpm": 140
      }
    },
    {
      "start": 0.25,
      "duration": 0.5,
      "type": "note",
      "meta": {
        "pitch": 60,
        "velocity": 100,
        "sample": "examples/data/samples/piano_A.wav",
        "base_note": 60,
        "layer": "keys",
        "visual": {
          "image": "examples/data/samples/placeholder.png",
          "effects": ["zoom"],
          "opacity": 0.95,
          "position": "center"
        }
      }
    },
    {
      "start": 0.8,
      "duration": 0.18,
      "type": "note",
      "meta": {
        "pitch": 72,
        "velocity": 110,
        "sample": "examples/data/samples/vocal_hit.wav",
        "semitones": 0,
        "layer": "vocals",
        "visual": {
          "image": "examples/data/samples/placeholder.png",
          "effects": ["color_shift"],
          "opacity": 1.0,
          "position": "center"
        }
      }
    },
    {
      "start": 1.5,
      "duration": 2.0,
      "type": "note",
      "meta": {
        "pitch": 48,
        "velocity": 100,
        "sample": "examples/data/samples/bass_loop.wav",
        "layer": "bass",
        "visual": {
          "image": "examples/data/samples/placeholder.png",
          "effects": ["zoom", "color_shift"],
          "opacity": 0.9,
          "position": "center"
        }
      }
    },
    {
      "start": 3.8,
      "duration": 0.5,
      "type": "note",
      "meta": {
        "pitch": 64,
        "velocity": 100,
        "sample": "examples/data/samples/piano_A.wav",
        "semitones": -3,
        "layer": "keys",
        "visual": {
          "image": "examples/data/samples/placeholder.png",
          "effects": ["shake"],
          "opacity": 0.95,
          "position": "center"
        }
      }
    },
    {
      "start": 5.0,
      "duration": 0.2,
      "type": "note",
      "meta": {
        "pitch": 76,
        "velocity": 120,
        "sample": "examples/data/samples/vocal_hit.wav",
        "semitones": 4,
        "layer": "vocals",
        "visual": {
          "image": "examples/data/samples/placeholder.png",
          "effects": ["zoom", "color_shift"],
          "opacity": 1.0,
          "position": "center"
        }
      }
    },
    {
      "start": 7.0,
      "duration": 5.0,
      "type": "note",
      "meta": {
        "pitch": 36,
        "velocity": 100,
        "sample": "examples/data/samples/bass_loop.wav",
        "layer": "bass",
        "visual": {
          "image": "examples/data/samples/placeholder.png",
          "effects": [],
          "opacity": 0.85,
          "position": "center"
        }
      }
    }
  ]
}
```

How to adapt this tutorial project
- Paths: `sample_map` references are relative to the repository root in the examples above. Adjust to match your local layout or use absolute paths.
- Samples: replace the sample files with your own WAVs (recommended) for better audio quality and auditioning.
- Visuals: `visual` entries can point to images or videos; effects may be names registered in the VideoRenderer (`zoom`, `shake`, `color_shift`) or callables set programmatically.
- Pitching: supply `base_note` for a sample (MIDI number) so the renderer can compute semitone shifts automatically when an event's `pitch` differs from the sample's `base_note`. `semitones` can be used to force an offset.
- Tempo: `meta.base_bpm` or tempo events control tempo-aware behavior. The renderer's `tempo_bpm` parameter can override or scale playback.
- Layers: use `meta.layer` to group visuals and control z-ordering manually in your VideoRenderer usage.

Quick workflow
1. Save the JSON as `tutorial-song.ytpmv.json`.
2. Open it in the Editor: `run_editor(Project.load("tutorial-song.ytpmv.json"))` or use the GUI Load button.
3. Assign or validate sample paths (Assign Sample) and save.
4. From command line, render:

```bash
ytpmv render --project tutorial-song.ytpmv.json --out tutorial-song.mp4 --chunk 8 --workers 2
```

Troubleshooting tips
- If samples don't play in the Editor playback, ensure `simpleaudio` is installed and samples are WAV.
- If rendering fails due to ffmpeg error, ensure ffmpeg is installed and available on PATH.
- If OpenMPT parsing is relevant: this JSON assumes you already created/edited events; to generate a similar project from a tracker file, parse it (`ytpmv parse --format openmpt song.it --out tutorial-song.ytpmv.json`) and then refine in the Editor.

That's it — use this starter project to experiment with chunked rendering, tempo-aware behavior, pitch shifts, and layered visuals. If you want, I can produce a ZIP with example WAVs and placeholder images you can drop into `examples/data/` so this project works out-of-the-box.