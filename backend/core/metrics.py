"""
In-process metrics store.
Tracks latency and token usage per request — accessible via /metrics endpoint.
"""

import time
import threading
from collections import deque
from typing import Dict, Any, List

_lock = threading.Lock()

# Rolling window — last 1000 requests
_events: deque = deque(maxlen=1000)


def record(event: Dict[str, Any]) -> None:
    """Append a metrics event (called after each /ask)."""
    event["ts"] = time.time()
    with _lock:
        _events.append(event)


def snapshot() -> Dict[str, Any]:
    """Return a summary of all recorded events."""
    with _lock:
        events: List[Dict] = list(_events)

    if not events:
        return {"total_requests": 0}

    latencies = [e["latency_ms"] for e in events if "latency_ms" in e]
    prompt_tokens = [e["prompt_tokens"] for e in events if "prompt_tokens" in e]
    completion_tokens = [e["completion_tokens"] for e in events if "completion_tokens" in e]

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else 0

    return {
        "total_requests": len(events),
        "latency_ms": {
            "avg": avg(latencies),
            "min": round(min(latencies), 1) if latencies else 0,
            "max": round(max(latencies), 1) if latencies else 0,
        },
        "tokens": {
            "prompt_total": sum(prompt_tokens),
            "completion_total": sum(completion_tokens),
            "prompt_avg": avg(prompt_tokens),
            "completion_avg": avg(completion_tokens),
        },
        "recent": events[-5:][::-1],   # last 5, newest first
    }