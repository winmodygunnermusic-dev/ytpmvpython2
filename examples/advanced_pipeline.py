"""
Advanced example: shows OpenMPT parsing, batching logic, layered visuals, and GUI preview.

You must adapt OPENMPT_CMD in ytpmpython/parser/openmpt_parser.py to point to your exporter.
"""

from ytpmpython.logging_config import setup_logging
from ytpmpython.parser.base import get_parser_for_format
from ytpmpython.samples.registry import SampleRegistry
from ytpmpython.renderer.audio_renderer import AudioRenderer
from ytpmpython.renderer.video_renderer import VideoRenderer
from ytpmpython.gui.preview import preview_timeline
from ytpmpython.utils.cache import FileCache
from ytpmpython.utils.timeline import batch_nearby_events
import os

setup_logging(debug=True)

# Example: parse an OpenMPT module
parser = get_parser_for_format("openmpt")
events = parser.parse("examples/data/example.it")

# Batch nearby events for more efficient mixing decisions
batches = batch_nearby_events(events, proximity=0.2)
print("Batches:", len(batches))

# Register samples
reg = SampleRegistry()
reg.register("vocal", "examples/data/samples/vocal_hit.wav")
reg.register("bass", "examples/data/samples/bass_loop.wav")

# Assign visual layers for first N events
for i, e in enumerate(events[:20]):
    e.meta.setdefault("visual", {})
    e.meta["visual"]["image"] = "examples/data/samples/placeholder.png"
    e.meta["visual"]["effects"] = ["shake" if i % 2 == 0 else "zoom"]
    e.meta["layer"] = f"layer_{i%3}"

cache = FileCache(".example_cache_adv")
audio_renderer = AudioRenderer(reg, cache=cache, debug=True)
os.makedirs("out", exist_ok=True)
audio_out = "out/advanced_audio.wav"
audio_renderer.render(events, audio_out, chunk_size=6.0, tempo_bpm=140.0, max_workers=3, cache_age=7200)

video_renderer = VideoRenderer(duration=max(e.start + e.duration for e in events), bg_color=(5,5,10))
video_out = "out/advanced_video.mp4"
video_renderer.render(events, audio_out, video_out, default_image="examples/data/samples/placeholder.png", fps=30)

preview_timeline(events[:40])
print("Advanced pipeline complete.")