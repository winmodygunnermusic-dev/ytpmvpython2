"""
Video composition: layered clips + effect registry.

This module provides simple compositing and a registry-driven effects pipeline.
"""

from typing import List, Optional, Callable, Dict, Any
from ..events import Event
import logging
from moviepy.editor import ColorClip, ImageClip, VideoFileClip, CompositeVideoClip
import numpy as np

logger = logging.getLogger(__name__)

Effect = Callable[[Any], Any]
_EFFECTS: Dict[str, Effect] = {}

def register_effect(name: str, fn: Effect) -> None:
    _EFFECTS[name] = fn

def zoom_effect(clip, scale_end: float = 1.2):
    return clip.resize(lambda t: 1.0 + (scale_end - 1.0) * (t / (clip.duration or 1.0)))

def color_shift(clip, amount: float = 0.12):
    import numpy as np
    return clip.fl_image(lambda fr: np.clip(fr.astype(np.float32) * (1.0 + np.array([amount, 0.0, -amount/2])), 0, 255).astype('uint8'))

register_effect("zoom", zoom_effect)
register_effect("color_shift", color_shift)

class VideoRenderer:
    def __init__(self, duration: float, size=(1280,720), bg_color=(0,0,0), fps: int = 24):
        self.duration = duration
        self.size = size
        self.bg_color = bg_color
        self.fps = fps

    def render(self, events: List[Event], audio_path: Optional[str], out_path: str, default_image: Optional[str] = None, verbose: bool = False):
        bg = ColorClip(size=self.size, color=self.bg_color, duration=self.duration).set_fps(self.fps)
        clips = [bg]
        for e in events:
            vis = e.meta.get("visual", {})
            path = vis.get("image") or vis.get("video") or default_image
            if not path:
                continue
            try:
                if vis.get("video"):
                    clip = VideoFileClip(path).subclip(0, min(e.duration, VideoFileClip(path).duration))
                else:
                    clip = ImageClip(path).set_duration(e.duration)
            except Exception:
                continue
            effects = vis.get("effects", [])
            for ef in effects:
                if isinstance(ef, str):
                    fn = _EFFECTS.get(ef)
                    if fn:
                        clip = fn(clip)
                elif callable(ef):
                    clip = ef(clip)
            clip = clip.set_start(e.start).set_pos(vis.get("position", "center")).set_opacity(vis.get("opacity", 1.0))
            clips.append(clip)
        comp = CompositeVideoClip(clips, size=self.size).set_duration(self.duration)
        if audio_path:
            try:
                from moviepy.editor import AudioFileClip
                comp = comp.set_audio(AudioFileClip(audio_path))
            except Exception:
                pass
        comp.write_videofile(out_path, fps=self.fps, codec="libx264", audio_codec="aac", verbose=verbose)
        comp.close()
        logger.info("Video written: %s", out_path)