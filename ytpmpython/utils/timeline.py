"""
Utilities for chunking and batching timelines to support large projects.
"""

from typing import Iterable, List, Tuple
from ..events import Event
import math

def chunk_timeline(events: Iterable[Event], chunk_size: float) -> List[Tuple[float, float, List[Event]]]:
    """
    Split events into chunks of duration `chunk_size` seconds.

    Returns list of tuples (chunk_start, chunk_end, [events_in_chunk]).
    Overlapping events that cross chunk boundaries are included in both chunks
    (renderers should clip appropriately).
    """
    evts = list(events)
    if not evts:
        return []
    start = min(e.start for e in evts)
    end = max(e.start + e.duration for e in evts)
    chunks = []
    t = start
    while t < end:
        chunk_start = t
        chunk_end = t + chunk_size
        in_chunk = [e for e in evts if not (e.start >= chunk_end or (e.start + e.duration) <= chunk_start)]
        chunks.append((chunk_start, chunk_end, in_chunk))
        t = chunk_end
    return chunks

def batch_nearby_events(events: Iterable[Event], proximity: float) -> List[List[Event]]:
    """
    Group nearby events: events within `proximity` seconds of each other are batched.
    Returns list of event lists.
    """
    evts = sorted(events, key=lambda e: e.start)
    batches = []
    if not evts:
        return batches
    current_batch = [evts[0]]
    for e in evts[1:]:
        if e.start - (current_batch[-1].start + current_batch[-1].duration) <= proximity:
            current_batch.append(e)
        else:
            batches.append(current_batch)
            current_batch = [e]
    batches.append(current_batch)
    return batches