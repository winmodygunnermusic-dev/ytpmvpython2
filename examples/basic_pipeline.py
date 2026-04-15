"""
Basic example pipeline: parse a MIDI file, register samples, render audio and a simple video.

Usage:
    python examples/basic_pipeline.py
"""

from ytpmpython.logging_config import setup_logging
from ytpmpython.parser.base import get_parser_for_format
from ytpmpython.samples.registry import SampleRegistry
from ytpmpython.renderer.audio_renderer import AudioRenderer
from ytpmpython.renderer.video_renderer import VideoRenderer
from ytpmpython.utils.cache import FileCache
import os

setup_logging(debug=True)

# Parse MIDI file
parser = get_parser_for_format("midi")
events = parser.parse("examples/data/example.mid")  # ensure you have an example MIDI

# Setup samples
reg = SampleRegistry()
reg.register("piano_A", "examples/data/samples/piano_A.wav")
reg.register("vocal_hit", "examples/data/samples/vocal_hit.wav")

# Map event sample names to files (fallback)
sample_paths = {
    "piano_A": "examples/data/samples/piano_A.wav",
    "vocal_hit": "examples/data/samples/vocal_hit.wav",
}

cache = FileCache(".example_cache")
audio_renderer = AudioRenderer(reg, sample_paths=sample_paths, cache=cache, debug=True)

os.makedirs("out", exist_ok=True)
audio_out = "out/basic_audio.wav"
audio_renderer.render(events, audio_out, chunk_size=8.0, tempo_bpm=120.0, max_workers=2, cache_age=3600)

# Simple video render: create visuals for the first few notes
for e in events[:6]:
    e.meta["visual"] = {"image": "examples/data/samples/placeholder.png", "effects": ["zoom", "color_shift"], "opacity": 0.9}

video_renderer = VideoRenderer(duration=max((ev.start + ev.duration) for ev in events), bg_color=(10,10,10))
video_out = "out/basic_video.mp4"
video_renderer.render(events, audio_out, video_out, default_image="examples/data/samples/placeholder.png")
print("Basic pipeline complete: ", audio_out, video_out)