"""
Small file cache keyed by hash.
"""

from typing import Optional
import os
import hashlib
import time

class FileCache:
    def __init__(self, directory: str = ".ytpmv_cache"):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, key: str) -> str:
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return os.path.join(self.directory, f"{h}.bin")

    def get(self, key: str, max_age: Optional[int] = None) -> Optional[bytes]:
        p = self._path(key)
        if not os.path.exists(p):
            return None
        if max_age is not None:
            if time.time() - os.path.getmtime(p) > max_age:
                try:
                    os.remove(p)
                except Exception:
                    pass
                return None
        with open(p, "rb") as fh:
            return fh.read()

    def set(self, key: str, data: bytes) -> None:
        p = self._path(key)
        with open(p, "wb") as fh:
            fh.write(data)

    def clear(self) -> None:
        for fn in os.listdir(self.directory):
            try:
                os.remove(os.path.join(self.directory, fn))
            except Exception:
                pass