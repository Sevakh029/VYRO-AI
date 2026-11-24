import math
from threading import Lock


class LatencyHistogram:
    def __init__(self, bucket_ms: int = 100) -> None:
        if bucket_ms <= 0:
            raise ValueError("bucket_ms must be positive")
        self.bucket_ms = bucket_ms
        self._samples_ms: list[float] = []
        self._lock = Lock()

    def record_seconds(self, latency_s: float) -> None:
        if not math.isfinite(latency_s) or latency_s < 0:
            raise ValueError("latency must be finite and non-negative")
        with self._lock:
            self._samples_ms.append(latency_s * 1000.0)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            samples = list(self._samples_ms)
        buckets: dict[str, int] = {}
        for sample in samples:
            bucket = int(sample // self.bucket_ms) * self.bucket_ms
            key = f"{bucket}-{bucket + self.bucket_ms}ms"
            buckets[key] = buckets.get(key, 0) + 1
        return {
            "count": len(samples),
            "mean_ms": sum(samples) / len(samples) if samples else 0.0,
            "buckets": dict(sorted(buckets.items())),
        }
