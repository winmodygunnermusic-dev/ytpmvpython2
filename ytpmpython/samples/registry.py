"""
Sample registry and lazy loader utilities.
"""

from typing import Dict, Optional
from moviepy.audio.io.AudioFileClip import AudioFileClip
import logging

logger = logging.getLogger(__name__)

class SampleRegistry:
    def __init__(self):
        self._map: Dict[str, str] = {}
        self._cache: Dict[str, AudioFileClip] = {}

    def register(self, name: str, path: str) -> None:
        self._map[name] = path
        logger.debug("Sample registered: %s -> %s", name, path)

    def get_path(self, name: str) -> Optional[str]:
        return self._map.get(name)

    def get_clip(self, name: str) -> Optional[AudioFileClip]:
        if name is None:
            return None
        if name in self._cache:
            return self._cache[name]
        path = self._map.get(name)
        if not path:
            logger.warning("Sample %s not found", name)
            return None
        clip = AudioFileClip(path)
        self._cache[name] = clip
        return clip

    def clear(self):
        for c in self._cache.values():
            try:
                c.close()
            except Exception:
                pass
        self._cache.clear()