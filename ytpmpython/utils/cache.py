"""
Simple file-based cache keyed by strings. Uses hashed filenames.
Useful for caching rendered chunks.
"""

import hashlib
import json
import os
from typing import Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

class FileCache:
    def __init__(self, cache_dir: str = ".ytpmv_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.cache")

    def get(self, key: str, max_age_seconds: Optional[int] = None) -> Optional[bytes]:
        path = self._key_to_path(key)
        if not os.path.exists(path):
            return None
        if max_age_seconds is not None:
            age = time.time() - os.path.getmtime(path)
            if age > max_age_seconds:
                try:
                    os.remove(path)
                except Exception:
                    pass
                return None
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except Exception as exc:
            logger.debug("Cache read failed: %s", exc)
            return None

    def set(self, key: str, data: bytes) -> None:
        path = self._key_to_path(key)
        with open(path, "wb") as fh:
            fh.write(data)

    def clear(self) -> None:
        for fn in os.listdir(self.cache_dir):
            try:
                os.remove(os.path.join(self.cache_dir, fn))
            except Exception:
                pass