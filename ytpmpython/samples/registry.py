"""
SampleRegistry: small registry for named samples and loaders.

Samples are referenced by name in NoteEvent.meta['sample'].
Registry keeps paths and lazy-loads AudioFileClip objects when needed.

Note: MoviePy AudioFileClip is used for on-disk sample loading. The registry
exposes a helper to return a MoviePy AudioFileClip or None if not found.
"""

from typing import Dict, Optional
import logging
from moviepy.audio.io.AudioFileClip import AudioFileClip

logger = logging.getLogger(__name__)

class SampleRegistry:
    """
    Registry of reusable samples.

    Usage:
        reg = SampleRegistry()
        reg.register("vocal_A", "samples/vocal_A.wav")
        clip = reg.get("vocal_A")  # returns AudioFileClip
    """

    def __init__(self):
        self._map: Dict[str, str] = {}
        self._cache: Dict[str, AudioFileClip] = {}

    def register(self, name: str, path: str) -> None:
        """Register a sample name to a file path."""
        self._map[name] = path
        logger.debug("Registered sample %s -> %s", name, path)

    def get_path(self, name: str) -> Optional[str]:
        return self._map.get(name)

    def get(self, name: str) -> Optional[AudioFileClip]:
        """Return a MoviePy AudioFileClip, cached after first load."""
        if name is None:
            return None
        if name in self._cache:
            return self._cache[name]
        path = self._map.get(name)
        if not path:
            logger.warning("Sample %s not found in registry", name)
            return None
        clip = AudioFileClip(path)
        self._cache[name] = clip
        return clip

    def clear_cache(self) -> None:
        for c in self._cache.values():
            try:
                c.close()
            except Exception:
                pass
        self._cache.clear()