from collections import defaultdict, deque
from threading import Lock
from time import time


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: tuple[str, str], now: float) -> None:
        failures = self._failures.get(key)
        if failures is None:
            return

        cutoff = now - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()

        if not failures:
            self._failures.pop(key, None)

    def retry_after(self, email: str, client_ip: str, now: float | None = None) -> int | None:
        current = time() if now is None else now
        key = (email.strip().lower(), client_ip)

        with self._lock:
            self._prune(key, current)
            failures = self._failures.get(key)
            if failures is None or len(failures) < self.max_attempts:
                return None

            return max(1, int(failures[0] + self.window_seconds - current + 0.999))

    def record_failure(self, email: str, client_ip: str, now: float | None = None) -> None:
        current = time() if now is None else now
        key = (email.strip().lower(), client_ip)

        with self._lock:
            self._prune(key, current)
            self._failures[key].append(current)

    def record_success(self, email: str, client_ip: str) -> None:
        key = (email.strip().lower(), client_ip)

        with self._lock:
            self._failures.pop(key, None)

    def cleanup(self, now: float | None = None) -> None:
        current = time() if now is None else now

        with self._lock:
            for key in list(self._failures):
                self._prune(key, current)
