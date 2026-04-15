"""
Timeline helpers: chunking and batching.
"""

from typing import Iterable, List, Tuple
from ..events import Event

def chunk_timeline(events: Iterable[Event], chunk_size: float) -> List[Tuple[float, float, List[Event]]]:
    evts = list(events)
    if not evts:
        return []
    start = min(e.start for e in evts)
    end = max(e.start + e.duration for e in evts)
    out = []
    t = start
    while t < end:
        cs = t
        ce = t + chunk_size
        in_chunk = [e for e in evts if not (e.start >= ce or (e.start + e.duration) <= cs)]
        out.append((cs, ce, in_chunk))
        t = ce
    return out

def batch_nearby(events: Iterable[Event], proximity: float) -> List[List[Event]]:
    evts = sorted(events, key=lambda e: e.start)
    if not evts:
        return []
    batches = []
    cur = [evts[0]]
    for e in evts[1:]:
        last = cur[-1]
        if e.start - (last.start + last.duration) <= proximity:
            cur.append(e)
        else:
            batches.append(cur)
            cur = [e]
    batches.append(cur)
    return batches