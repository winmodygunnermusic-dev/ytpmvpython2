"""
VideoRenderer with layered compositing and effects.

Uses MoviePy to layer clips per-event and synchronize with an audio timeline.
Supports an effect pipeline: functions that accept a VideoClip and return a transformed clip.

Visual effects examples implemented:
- zoom_effect: zoom-in over event duration
- shake_effect: small randomized translation
- color_shift_effect: simple color multiplier via fl_image

Each Event.meta may contain:
    - layer: str or int to route to a particular layer
    - visual: dict with keys: 'image' or 'video' file path, 'effects': list of effects names, 'opacity', etc.
"""

from typing import List, Callable, Dict, Any, Optional
from ..events import Event
import logging
from moviepy.editor import (VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips,
                            ColorClip)
import numpy as np
import random

logger = logging.getLogger(__name__)

Effect = Callable[[Any, float], Any]  # (clip, event_start) -> clip

def zoom_effect(clip, event_start: float, scale_start: float = 1.0, scale_end: float = 1.2):
    """Return clip that zooms from scale_start to scale_end over its duration."""
    def make_frame(get_frame, t):
        # scale factor at local time t
        duration = clip.duration or 0.001
        factor = scale_start + (scale_end - scale_start) * (t / duration)
        frame = get_frame(t)
        h, w = frame.shape[:2]
        # compute new size and crop center
        new_w = int(w / factor)
        new_h = int(h / factor)
        x0 = max(0, (w - new_w) // 2)
        y0 = max(0, (h - new_h) // 2)
        cropped = frame[y0:y0+new_h, x0:x0+new_w]
        # resize back to original
        from moviepy.video.fx.all import resize
        return resize(ImageClip(cropped).set_duration(clip.duration).get_frame)(t)
    # Using MoviePy transforms directly is more reliable; here we use fx.resize with lambda
    return clip.resize(lambda t: 1.0 + (scale_end - scale_start) * (t / (clip.duration or 1.0)))

def shake_effect(clip, intensity: float = 8.0):
    """Apply a shaking translation effect to the clip."""
    from moviepy.video.fx.all import crop
    def transform(get_frame, t):
        frame = get_frame(t)
        dx = int((random.random() - 0.5) * intensity)
        dy = int((random.random() - 0.5) * intensity)
        # pad and then crop to create translation
        h, w = frame.shape[:2]
        padded = np.pad(frame, ((max(10, intensity), max(10, intensity)), (max(10, intensity), max(10, intensity)), (0, 0)), mode='edge')
        y0 = max(0, int(padded.shape[0]//2 - h//2 + dy))
        x0 = max(0, int(padded.shape[1]//2 - w//2 + dx))
        return padded[y0:y0+h, x0:x0+w]
    return clip.fl_image(lambda im: transform(lambda t: im, 0))  # approximate static transform

def color_shift_effect(clip, shift: float = 0.1):
    """Apply a simple per-frame color multiplier (adds to red channel)."""
    def fl(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        frame[..., 0] = np.clip(frame[..., 0] + 255.0 * shift, 0, 255)
        return frame.astype('uint8')
    return clip.fl_image(lambda frame: np.clip(frame.astype(np.float32) * (1.0 + np.array([shift, -shift/2, -shift/2])), 0, 255).astype('uint8'))

_EFFECT_REGISTRY: Dict[str, Callable[..., Any]] = {
    "zoom": zoom_effect,
    "shake": shake_effect,
    "color_shift": color_shift_effect,
}

class VideoRenderer:
    """
    Compose video by layering clips per event.

    Arguments:
        duration: total output duration in seconds
        bg_color: background color tuple or CSS-like string
    """

    def __init__(self, duration: float, bg_color=(0,0,0)):
        self.duration = duration
        self.bg_color = bg_color

    def render(self, events: List[Event], audio_path: Optional[str], out_path: str,
               default_image: Optional[str] = None, fps: int = 24, verbose: bool = False) -> None:
        """
        Build a CompositeVideoClip from events. Each event.meta may include 'visual' with keys:
            - 'image': path to an image
            - 'video': path to a video
            - 'effects': list of effect names to apply
            - 'opacity': float
            - 'position': tuple or 'center'
        """
        base = ColorClip(size=(1280,720), color=self.bg_color, duration=self.duration).set_fps(fps)
        clips = [base]
        for e in events:
            vis = e.meta.get("visual", {})
            media_path = vis.get("video") or vis.get("image") or default_image
            if not media_path:
                continue
            if vis.get("video"):
                clip = VideoFileClip(media_path).subclip(0, min(e.duration, VideoFileClip(media_path).duration))
            else:
                clip = ImageClip(media_path).set_duration(e.duration)
            # Apply effects
            effects = vis.get("effects", [])
            for eff in effects:
                if isinstance(eff, str):
                    eff_fn = _EFFECT_REGISTRY.get(eff)
                    if eff_fn:
                        clip = eff_fn(clip)
                elif callable(eff):
                    clip = eff(clip)
            pos = vis.get("position", "center")
            opacity = vis.get("opacity", 1.0)
            clip = clip.set_start(e.start).set_pos(pos).set_opacity(opacity)
            clips.append(clip)
        composite = CompositeVideoClip(clips, size=(1280,720)).set_duration(self.duration)
        if audio_path:
            # Attach audio using MoviePy's VideoFileClip audio assignment (works with audio file)
            try:
                from moviepy.editor import AudioFileClip
                audio = AudioFileClip(audio_path)
                composite = composite.set_audio(audio)
            except Exception:
                pass
        composite.write_videofile(out_path, fps=fps, codec="libx264", audio_codec="aac", verbose=verbose)
        composite.close()
        logger.info("Video rendering complete: %s", out_path)