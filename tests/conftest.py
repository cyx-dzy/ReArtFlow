import time

import pytest


class _BenchmarkStats:
    mean = 0.0


class _SimpleBenchmark:
    def __init__(self):
        self.stats = _BenchmarkStats()

    def __call__(self, func, *args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        self.stats.mean = time.perf_counter() - start
        return result


@pytest.fixture
def benchmark():
    return _SimpleBenchmark()
