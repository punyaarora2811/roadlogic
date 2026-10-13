"""
groq_rate_limiter.py
====================
Thread-safe rate limiter and token-budget guardian for the Groq API.
Enforces pacing between API requests across all threads (traffic director and
vehicle agents) to remain safely within the free-tier TPM (Tokens Per Minute) limit.
"""

import time
import threading


class GroqRateLimiter:
    def __init__(self, min_interval=1.5):
        self.min_interval = min_interval
        self.last_call_time = 0.0
        self.lock = threading.Lock()
        self.cooldown_until = 0.0

    def acquire(self, timeout=1.5) -> bool:
        """
        Wait up to `timeout` seconds to acquire permission to make an API call.
        Returns True if safely permitted; False if in cooldown or timed out.
        """
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                now = time.time()
                if now < self.cooldown_until:
                    return False
                wait_needed = self.min_interval - (now - self.last_call_time)
                if wait_needed <= 0:
                    self.last_call_time = time.time()
                    return True
            time.sleep(0.05)
        return False

    def report_429(self, backoff_seconds=5.0):
        """Put the limiter into a temporary backoff cooldown to let the token bucket recover."""
        with self.lock:
            self.cooldown_until = time.time() + backoff_seconds


# Global singleton rate limiter shared across all vehicle agents and spawner
rate_limiter = GroqRateLimiter(min_interval=1.5)
