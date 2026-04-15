"""
Chunk-based, parallel audio renderer.

Simplified, but production-oriented:
- Splits timeline into chunks
- Renders chunks in ProcessPoolExecutor workers that produce temporary WAVs
- Concatenates final audio via MoviePy
- Supports basic semitone pitch shift via resampling (naive)
- Supports tempo multiplier (speed)
- Uses FileCache if provided
"""

from typing import List, Optional, Dict, Tuple
from ..events import Event, NoteEvent
from ..samples.registry import SampleRegistry
from ..utils.cache import FileCache
from ..utils.timeline import chunk_timeline
import numpy as np
import tempfile
import os
import hashlib
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import concatenate_audioclips

logger = logging.getLogger(__name__)
DEFAULT_SR = 44100

def _chunk_hash(cs: float, ce: float, events: List[Event], tempo: float, extra: str = "") -> str:
    m = hashlib.sha1()
    m.update(f"{cs:.6f}-{ce:.6f}-{tempo}-{extra}".encode("utf-8"))
    for e in events:
        m.update(repr((e.start, e.duration, e.type, tuple(sorted(e.meta.items())))).encode("utf-8"))
    return m.hexdigest()

def _render_chunk(args):
    # args is a serializable tuple
    cs, ce, events, sample_map, sr, tmp_path, tempo_mul = args
    import numpy as np
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    n = int(np.ceil((ce - cs) * sr))
    mix = np.zeros((n, 2), dtype=np.float32)
    def load_sample_np(path: str):
        clip = AudioFileClip(path)
        arr = clip.to_soundarray(fps=sr)
        clip.close()
        return arr
    for e in events:
        if e.type != "note":
            continue
        meta = e.meta
        sample_path = meta.get("sample") or sample_map.get(meta.get("sample"))
        if not sample_path or not os.path.exists(sample_path):
            continue
        try:
            sarr = load_sample_np(sample_path)
        except Exception:
            continue
        # pitch shift by semitones (naive resample)
        semis = float(meta.get("semitones", 0.0))
        base_note = meta.get("base_note")
        pitch = meta.get("pitch")
        if pitch is not None and base_note is not None:
            semis = float(pitch - base_note)
        if abs(semi:=semitones := semis) > 0.001:
            factor = 2.0 ** (semitones / 12.0)
            old_len = sarr.shape[0]
            new_len = max(1, int(round(old_len / factor)))
            x_old = np.linspace(0.0, 1.0, old_len)
            x_new = np.linspace(0.0, 1.0, new_len)
            sarr = np.stack([np.interp(x_new, x_old, sarr[:, ch]) for ch in range(sarr.shape[1])], axis=1)
        # tempo adjust (speed)
        if tempo_mul and tempo_mul != 1.0:
            factor = tempo_mul
            old_len = sarr.shape[0]
            new_len = max(1, int(round(old_len / factor)))
            x_old = np.linspace(0.0, 1.0, old_len)
            x_new = np.linspace(0.0, 1.0, new_len)
            sarr = np.stack([np.interp(x_new, x_old, sarr[:, ch]) for ch in range(sarr.shape[1])], axis=1)
        offset = int(round((e.start - cs) * sr))
        if offset < -sarr.shape[0]:
            continue
        dst0 = max(0, offset)
        src0 = max(0, -offset)
        length = min(n - dst0, sarr.shape[0] - src0)
        if length > 0:
            mix[dst0:dst0+length] += sarr[src0:src0+length][:length]
    maxv = np.max(np.abs(mix)) if mix.size else 0.0
    if maxv > 1.0:
        mix = mix / (maxv + 1e-9)
    clip = AudioArrayClip(mix, fps=sr)
    clip.write_audiofile(tmp_path, fps=sr, nbytes=2, bitrate="192k", verbose=False, logger=None)
    clip.close()
    with open(tmp_path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    return data

class AudioRenderer:
    def __init__(self, samples: SampleRegistry, sample_paths: Optional[Dict[str,str]] = None, cache: Optional[FileCache] = None, sr: int = DEFAULT_SR):
        self.samples = samples
        self.sample_paths = sample_paths or {}
        self.cache = cache
        self.sr = sr

    def render(self, events: List[Event], out_path: str, chunk_size: float = 8.0, tempo_bpm: Optional[float] = None, workers: int = 2, cache_age: Optional[int] = None):
        tempo_mul = 1.0
        if tempo_bpm:
            tempo_mul = 120.0 / float(tempo_bpm)
        chunks = chunk_timeline(events, chunk_size)
        tasks = []
        for cs, ce, es in chunks:
            key = _chunk_hash(cs, ce, es, tempo_mul, extra="v2")
            tmp_path = os.path.join(tempfile.gettempdir(), f"ytpmv_chunk_{key}.wav")
            args = (cs, ce, es, {**self.samples._map, **(self.sample_paths or {})}, self.sr, tmp_path, tempo_mul)
            tasks.append((key, args, cs, ce))
        tmp_files = []
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = {}
            for key, args, cs, ce in tasks:
                if self.cache:
                    data = self.cache.get(key, max_age=cache_age)
                    if data:
                        p = os.path.join(tempfile.gettempdir(), f"ytpmv_chunk_{key}.wav")
                        with open(p, "wb") as fh:
                            fh.write(data)
                        tmp_files.append((cs, p))
                        continue
                futures[ex.submit(_render_chunk, args)] = (key, cs)
            for fut in as_completed(futures):
                key, cs = futures[fut]
                try:
                    data = fut.result()
                except Exception as exc:
                    logger.exception("Chunk failed: %s", exc)
                    continue
                p = os.path.join(tempfile.gettempdir(), f"ytpmv_chunk_{key}.wav")
                with open(p, "wb") as fh:
                    fh.write(data)
                tmp_files.append((cs, p))
                if self.cache:
                    try:
                        self.cache.set(key, data)
                    except Exception:
                        pass
        # order and concatenate
        tmp_files.sort(key=lambda t: t[0])
        clips = []
        for _, p in tmp_files:
            try:
                clips.append(AudioFileClip(p))
            except Exception:
                pass
        if not clips:
            # silence
            arr = np.zeros((int(0.1 * self.sr), 2), dtype=np.float32)
            AudioArrayClip(arr, fps=self.sr).write_audiofile(out_path, fps=self.sr, nbytes=2, bitrate="128k", verbose=False, logger=None)
            return
        final = concatenate_audioclips(clips)
        final.write_audiofile(out_path, fps=self.sr, nbytes=2, bitrate="192k", verbose=False, logger=None)
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        for _, p in tmp_files:
            try:
                os.remove(p)
            except Exception:
                pass
        logger.info("Audio render complete: %s", out_path)