"""Opt-in runtime profiling for Rebirth engine hot paths."""

from __future__ import annotations

from collections import defaultdict, deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Deque, Dict, Iterable, List, Optional


_ACTIVE_PROFILER: ContextVar[Optional["RebirthProfiler"]] = ContextVar("rebirth_active_profiler", default=None)


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


@dataclass
class MetricBucket:
    values: List[float] = field(default_factory=list)
    details: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    rolling: Deque[float] = field(default_factory=lambda: deque(maxlen=64))

    def record(self, elapsed_ms: float, detail: Optional[str] = None) -> None:
        elapsed_ms = float(elapsed_ms)
        self.values.append(elapsed_ms)
        self.rolling.append(elapsed_ms)
        if detail:
            self.details[str(detail)].append(elapsed_ms)

    def summary(self) -> Dict[str, Any]:
        values = self.values
        total = sum(values)
        count = len(values)
        detail_totals = {
            detail: {
                "count": len(items),
                "total_ms": round(sum(items), 6),
                "average_ms": round(sum(items) / len(items), 6) if items else 0.0,
                "max_ms": round(max(items), 6) if items else 0.0,
            }
            for detail, items in sorted(self.details.items())
        }
        return {
            "count": count,
            "total_ms": round(total, 6),
            "average_ms": round(total / count, 6) if count else 0.0,
            "max_ms": round(max(values), 6) if values else 0.0,
            "p95_ms": round(_percentile(values, 0.95), 6),
            "p99_ms": round(_percentile(values, 0.99), 6),
            "rolling_average_ms": round(sum(self.rolling) / len(self.rolling), 6) if self.rolling else 0.0,
            "details": detail_totals,
        }


class RebirthProfiler:
    def __init__(self, *, enabled: bool = True):
        self.enabled = bool(enabled)
        self._metrics: Dict[str, MetricBucket] = defaultdict(MetricBucket)
        self.deepest_effect_chain = 0
        self.largest_snapshot = {"bytes": 0, "reason": None}

    @contextmanager
    def active(self):
        token = _ACTIVE_PROFILER.set(self if self.enabled else None)
        try:
            yield self
        finally:
            _ACTIVE_PROFILER.reset(token)

    @contextmanager
    def timer(self, metric: str, detail: Optional[str] = None):
        if not self.enabled:
            yield None
            return
        started = perf_counter()
        try:
            yield self
        finally:
            self.record(metric, (perf_counter() - started) * 1000, detail=detail)

    def record(self, metric: str, elapsed_ms: float, *, detail: Optional[str] = None) -> None:
        if self.enabled:
            self._metrics[str(metric)].record(float(elapsed_ms), detail=detail)

    def observe_effect_chain_depth(self, depth: int) -> None:
        if self.enabled:
            self.deepest_effect_chain = max(self.deepest_effect_chain, int(depth or 0))

    def observe_snapshot_size(self, size_bytes: int, *, reason: Optional[str] = None) -> None:
        if self.enabled and int(size_bytes or 0) >= int(self.largest_snapshot.get("bytes") or 0):
            self.largest_snapshot = {"bytes": int(size_bytes or 0), "reason": reason}

    def hottest_detail(self, metric: str) -> Optional[Dict[str, Any]]:
        bucket = self._metrics.get(metric)
        if not bucket:
            return None
        hottest = None
        for detail, values in bucket.details.items():
            total = sum(values)
            if hottest is None or total > hottest["total_ms"]:
                hottest = {
                    "name": detail,
                    "count": len(values),
                    "total_ms": round(total, 6),
                    "average_ms": round(total / len(values), 6) if values else 0.0,
                    "max_ms": round(max(values), 6) if values else 0.0,
                }
        return hottest

    def summary(self) -> Dict[str, Any]:
        metrics = {name: bucket.summary() for name, bucket in sorted(self._metrics.items())}
        return {
            "enabled": self.enabled,
            "metrics": metrics,
            "hottest_reducer": self.hottest_detail("reducer_cost"),
            "deepest_effect_chain": self.deepest_effect_chain,
            "largest_snapshot": dict(self.largest_snapshot),
        }


def current_profiler() -> Optional[RebirthProfiler]:
    profiler = _ACTIVE_PROFILER.get()
    return profiler if profiler and profiler.enabled else None


@contextmanager
def debug_profile(*, enabled: bool = True):
    profiler = RebirthProfiler(enabled=enabled)
    with profiler.active():
        yield profiler
