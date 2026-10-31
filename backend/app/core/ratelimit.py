"""In-memory sliding-window rate limiter. Single process is enough for v1 (one user)."""

import math
import time
from collections import defaultdict, deque

from app.core.errors import AppError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, bucket: str, key: str, limit: int, window_s: float = 60.0) -> None:
        """Records a hit, or raises a 429 ``rate_limited`` error naming when to retry."""
        now = time.monotonic()
        hits = self._hits[(bucket, key)]
        while hits and now - hits[0] >= window_s:
            hits.popleft()
        if len(hits) >= limit:
            retry = max(1, math.ceil(window_s - (now - hits[0])))
            raise AppError(
                429,
                "You have sent several requests in a short time. Please wait a moment before trying again.",
                code="rate_limited",
                retry_after_sec=retry,
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()
