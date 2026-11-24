import random
import threading
from collections.abc import Callable


class PublishPath:
    def __init__(
        self,
        delay_seconds: float = 0.0,
        jitter_seconds: float = 0.0,
        drop_probability: float = 0.0,
        seed: int = 100,
    ) -> None:
        if delay_seconds < 0 or jitter_seconds < 0:
            raise ValueError("delay and jitter must be non-negative")
        if not 0.0 <= drop_probability <= 1.0:
            raise ValueError("drop_probability must be between 0 and 1")
        self.delay_seconds = delay_seconds
        self.jitter_seconds = jitter_seconds
        self.drop_probability = drop_probability
        self._random = random.Random(seed)
        self._timers: list[threading.Timer] = []

    def publish(
        self,
        publisher: Callable[[], object],
        wait_for_result: bool = False,
    ) -> object | None:
        if self._random.random() < self.drop_probability:
            return False
        delay = self.delay_seconds + self._random.uniform(0.0, self.jitter_seconds)
        if delay <= 0:
            return publisher()
        timer = threading.Timer(delay, publisher)
        if wait_for_result:
            timer.start()
            timer.join()
            return None
        self._timers.append(timer)
        timer.start()
        return None

    def close(self) -> None:
        for timer in self._timers:
            timer.cancel()
