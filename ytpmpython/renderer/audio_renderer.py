"""
Chunked, parallel audio renderer.

This renderer takes a list of events, a SampleRegistry, and renders audio per-chunk
(using numpy mixing). It supports simple pitch shifting by resampling (semitones),
tempo scale (BPM adjustments), caching, and parallel processing using
concurrent.futures.ProcessPoolExecutor.

Design choices:
- Use MoviePy's AudioArrayClip to create audio clips from numpy arrays.
- Per-chunk workers write temporary WAV files (via MoviePy) so we can safely
  combine them later without passing large numpy arrays between processes.
- Cache file bytes per chunk if a FileCache is provided.
"""

from typing import List, Optional, Tuple, Dict
from ..events import Event, NoteEvent, TempoEvent
from ..samples.registry import SampleRegistry
from ..utils.cache import FileCache
from ..utils.timeline import chunk_timeline
import numpy as np
import tempfile
import os
import logging
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.fx import all as afx
from moviepy.editor import concatenate_audioclips

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 44100

def _hash_for_chunk(chunk_start: float, chunk_end: float, events: List[Event], tempo: float, extra: Optional[str]) -> str:
    m = hashlib.sha1()
    m.update(f"{chunk_start:.6f}-{chunk_end:.6f}-{tempo}-{extra}".encode("utf-8"))
    for e in events:
        m.update(repr((e.start, e.duration, e.type, tuple(sorted(e.meta.items())))).encode("utf-8"))
    return m.hexdigest()

def _render_chunk_to_wav(args) -> bytes:
    """
    Worker to render a chunk to WAV bytes. Designed to be picklable-friendly
    (accepts simple args).
    """
    # Unpack args
    (chunk_start, chunk_end, events, sample_map, sample_paths, tempo, sr, tmpname) = args
    import numpy as np
    from moviepy.audio.AudioClip import AudioArrayClip
    # Prepare empty buffer
    n_samples = int(np.ceil((chunk_end - chunk_start) * sr))
    if n_samples <= 0:
        return b""
    mix = np.zeros((n_samples, 2), dtype=np.float32)  # stereo
    # Helper: load sample numpy array
    def load_sample(path: str):
        # We attempt to use moviepy AudioFileClip to read sample and get a numpy array
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        clip = AudioFileClip(path)
        arr = clip.to_soundarray(fps=sr)
        clip.close()
        return arr
    for e in events:
        if e.type != "note":
            continue
        meta = e.meta
        sample_name = meta.get("sample")
        sample_path = None
        if sample_name:
            sample_path = sample_map.get(sample_name) or sample_paths.get(sample_name)
        if not sample_path:
            # If sample path missing, skip
            continue
        # Load sample to numpy
        try:
            sample_arr = load_sample(sample_path)
        except Exception:
            continue
        # Determine pitch shift in semitones (if meta contains "pitch" or "semitones")
        semitones = float(meta.get("semitones", 0.0))
        pitch = meta.get("pitch")
        # If pitch is MIDI note, and sample has base_note, compute semitone diff
        base_note = meta.get("base_note")
        if pitch is not None and base_note is not None:
            semitones = float(pitch - base_note)
        # Resample if semitones != 0
        if abs(semitones) > 0.001:
            factor = 2.0 ** (semitones / 12.0)
            # naive resampling by interpolation along axis 0
            old_len = sample_arr.shape[0]
            new_len = max(1, int(np.round(old_len / factor)))
            x_old = np.linspace(0.0, 1.0, old_len)
            x_new = np.linspace(0.0, 1.0, new_len)
            sample_arr = np.stack([np.interp(x_new, x_old, sample_arr[:, ch]) for ch in range(sample_arr.shape[1])], axis=1)
        # Tempo scaling (simple time stretch via speed change)
        if tempo and tempo != 1.0:
            # tempo is a multiplier (1.0 default); adjust length by 1/tempo
            factor = tempo
            old_len = sample_arr.shape[0]
            new_len = max(1, int(np.round(old_len / factor)))
            x_old = np.linspace(0.0, 1.0, old_len)
            x_new = np.linspace(0.0, 1.0, new_len)
            sample_arr = np.stack([np.interp(x_new, x_old, sample_arr[:, ch]) for ch in range(sample_arr.shape[1])], axis=1)
        # Place sample relative to chunk_start
        event_offset = int(np.round((e.start - chunk_start) * sr))
        if event_offset < -len(sample_arr):
            continue
        s0 = max(0, event_offset)
        src0 = max(0, -event_offset)
        dst_len = min(n_samples - s0, sample_arr.shape[0] - src0)
        if dst_len > 0:
            mix[s0:s0+dst_len] += sample_arr[src0:src0+dst_len][:dst_len]
    # Normalize to prevent clipping
    max_val = np.max(np.abs(mix)) if mix.size else 0.0
    if max_val > 1.0:
        mix = mix / (max_val + 1e-9)
    # Convert to AudioArrayClip and write to wav bytes
    clip = AudioArrayClip(mix, fps=sr)
    out_path = tmpname
    clip.write_audiofile(out_path, fps=sr, nbytes=2, bitrate="192k", verbose=False, logger=None)
    clip.close()
    with open(out_path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(out_path)
    except Exception:
        pass
    return data

class AudioRenderer:
    """
    High-level audio renderer.

    Constructor arguments:
        sample_registry: SampleRegistry instance
        sample_paths: optional dict mapping sample name->path (fallback)
        cache: optional FileCache
        sample_rate: sample rate in Hz
    """

    def __init__(self, sample_registry: SampleRegistry,
                 sample_paths: Optional[Dict[str, str]] = None,
                 cache: Optional[FileCache] = None,
                 sample_rate: int = DEFAULT_SAMPLE_RATE,
                 debug: bool = False):
        self.registry = sample_registry
        self.sample_paths = sample_paths or {}
        self.cache = cache
        self.sr = sample_rate
        self.debug = debug
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

    def _prepare_chunk_args(self, chunk_start: float, chunk_end: float, events: List[Event], tempo_multiplier: float, extra: Optional[str]) -> Tuple:
        key = _hash_for_chunk(chunk_start, chunk_end, events, tempo_multiplier, extra)
        tmpname = os.path.join(tempfile.gettempdir(), f"ytpmv_chunk_{key}.wav")
        # Build sample_map (sample name to path) from registry
        sample_map = {}
        for name in self.registry._map:
            sample_map[name] = self.registry._map[name]
        return (chunk_start, chunk_end, events, sample_map, self.sample_paths, tempo_multiplier, self.sr, tmpname), key

    def render(self, events: List[Event], out_path: str, chunk_size: float = 10.0,
               tempo_bpm: Optional[float] = None, max_workers: int = 2, cache_age: Optional[int] = None) -> None:
        """
        Render events to out_path (wav). Splits timeline into chunk_size windows and renders in parallel.

        tempo_bpm: if provided, scales samples relative to base BPM (e.g. tempo-aware rendering).
        """
        # Determine tempo multiplier (if tempo_bpm provided)
        tempo_multiplier = 1.0
        if tempo_bpm:
            # If project uses 120 BPM as base, multiplier = (base_bpm / tempo_bpm). User may adapt.
            tempo_multiplier = 120.0 / float(tempo_bpm)
        chunks = chunk_timeline(events, chunk_size)
        # Prepare tasks
        tasks = []
        for chunk_start, chunk_end, chunk_events in chunks:
            (args, key) = self._prepare_chunk_args(chunk_start, chunk_end, chunk_events, tempo_multiplier, extra="v1")
            tasks.append((args, key, chunk_start, chunk_end))
        temp_files = []
        # Execute in parallel using ProcessPoolExecutor to avoid GIL issues and memory hog in main process
        with ProcessPoolExecutor(max_workers=max_workers) as ex:
            future_to_info = {}
            for args, key, cs, ce in tasks:
                if self.cache:
                    data = self.cache.get(key, max_age_seconds=cache_age)
                    if data:
                        # Write to temp file and skip worker
                        tmp_path = os.path.join(tempfile.gettempdir(), f"ytpmv_chunk_{key}.wav")
                        with open(tmp_path, "wb") as fh:
                            fh.write(data)
                        temp_files.append(tmp_path)
                        logger.debug("Cache hit for chunk %s", key)
                        continue
                future = ex.submit(_render_chunk_to_wav, args)
                future_to_info[future] = (key, cs, ce)
            # Collect results
            for future in as_completed(future_to_info):
                key, cs, ce = future_to_info[future]
                try:
                    data = future.result()
                except Exception as exc:
                    logger.exception("Chunk render failed: %s", exc)
                    continue
                tmp_path = os.path.join(tempfile.gettempdir(), f"ytpmv_chunk_{key}.wav")
                with open(tmp_path, "wb") as fh:
                    fh.write(data)
                temp_files.append(tmp_path)
                if self.cache:
                    self.cache.set(key, data)
        # Now load chunk files in order and concatenate them
        # Sort temp_files by chunk start timestamp encoded in name (we saved keys only, so sort by tasks order)
        # Simpler: read the tasks order and map keys to files
        key_to_file = {os.path.basename(p).split("ytpmv_chunk_")[-1].split(".wav")[0]: p for p in temp_files}
        ordered_clips = []
        for args, key, cs, ce in tasks:
            k = key
            path = key_to_file.get(k)
            if not path:
                # Possibly missing if chunk had no sound; create silent clip
                duration = max(0.0, ce - cs)
                if duration <= 0:
                    continue
                arr = np.zeros((int(duration * self.sr), 2), dtype=np.float32)
                clip = AudioArrayClip(arr, fps=self.sr)
            else:
                clip = AudioFileClip(path)
            ordered_clips.append(clip)
        if not ordered_clips:
            # Create a tiny silent file
            arr = np.zeros((int(0.1 * self.sr), 2), dtype=np.float32)
            clip = AudioArrayClip(arr, fps=self.sr)
            clip.write_audiofile(out_path, fps=self.sr, nbytes=2, bitrate="128k", verbose=False, logger=None)
            return
        final = concatenate_audioclips(ordered_clips)
        final.write_audiofile(out_path, fps=self.sr, nbytes=2, bitrate="192k", verbose=False, logger=None)
        # Close and clean up
        for c in ordered_clips:
            try:
                c.close()
            except Exception:
                pass
        for p in temp_files:
            try:
                os.remove(p)
            except Exception:
                pass
        logger.info("Audio rendering complete: %s", out_path)