from vyro_backend.latency import LatencyHistogram


def test_latency_histogram_records_buckets_and_mean() -> None:
    histogram = LatencyHistogram(bucket_ms=100)

    histogram.record_seconds(0.05)
    histogram.record_seconds(0.15)
    snapshot = histogram.snapshot()

    assert snapshot["count"] == 2
    assert snapshot["mean_ms"] == 100.0
    assert snapshot["buckets"] == {"0-100ms": 1, "100-200ms": 1}
