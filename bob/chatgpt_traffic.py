from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable, Sequence

CHATGPT_WRITE_TASK_TYPES = frozenset({
    "send_message",
    "cognition_request",
    "new_chat",
})
CHATGPT_FRESH_TASK_TYPES = frozenset({
    "cognition_request",
    "new_chat",
})
THROTTLE_PREFIX = "CHATGPT_TRANSIENT_UI:"


def throttle_category(result: dict | None) -> str | None:
    if not isinstance(result, dict) or result.get("success"):
        return None
    error = str(result.get("error") or "")
    if not error.startswith(THROTTLE_PREFIX):
        return None
    category = error[len(THROTTLE_PREFIX):].strip()
    return category or None


class ChatGPTTrafficController:
    """Serialize ChatGPT writes and pace fresh-chat creation.

    The browser bridge already owns a single Playwright worker. This controller
    adds policy at that shared choke point: cooldown after transient limits,
    fresh-chat spacing with jitter, and a fail-closed overlap guard.
    """

    def __init__(
        self,
        *,
        fresh_chat_min_interval_seconds: float = 10.0,
        jitter_seconds: float = 3.0,
        backoff_seconds: Sequence[float] = (15.0, 30.0, 60.0, 120.0),
        clock: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
        jitter_fn: Callable[[float, float], float] = random.uniform,
    ) -> None:
        interval = float(fresh_chat_min_interval_seconds)
        jitter = float(jitter_seconds)
        backoff = tuple(float(value) for value in backoff_seconds)
        if interval < 0 or jitter < 0:
            raise ValueError("traffic-control delays must be non-negative")
        if not backoff or any(value <= 0 for value in backoff):
            raise ValueError("backoff_seconds must contain positive values")
        if tuple(sorted(backoff)) != backoff:
            raise ValueError("backoff_seconds must be non-decreasing")

        self.fresh_chat_min_interval_seconds = interval
        self.jitter_seconds = jitter
        self.backoff_seconds = backoff
        self._clock = clock
        self._sleep = sleep_fn
        self._jitter = jitter_fn
        self._lock = threading.RLock()
        self._active_write = False
        self._last_fresh_attempt_at: float | None = None
        self._cooldown_until = 0.0
        self._throttle_streak = 0
        self._last_throttle_category: str | None = None

    @property
    def max_single_task_wait_seconds(self) -> float:
        return (
            max(self.backoff_seconds)
            + self.fresh_chat_min_interval_seconds
            + (2 * self.jitter_seconds)
        )

    def begin_task(self, task_type: str) -> dict:
        if task_type not in CHATGPT_WRITE_TASK_TYPES:
            return {"write_serialized": False, "cooldown_wait_seconds": 0.0}

        with self._lock:
            if self._active_write:
                raise RuntimeError("ChatGPT traffic controller detected overlapping writes")
            now = self._clock()
            wait_seconds = max(0.0, self._cooldown_until - now)

        if wait_seconds > 0:
            self._sleep(wait_seconds)

        with self._lock:
            if self._active_write:
                raise RuntimeError("ChatGPT traffic controller detected overlapping writes")
            self._active_write = True
            return {
                "write_serialized": True,
                "cooldown_wait_seconds": round(wait_seconds, 3),
                "throttle_streak": self._throttle_streak,
            }

    def before_fresh_chat(self) -> dict:
        with self._lock:
            now = self._clock()
            previous = self._last_fresh_attempt_at
            jitter = (
                self._jitter(0.0, self.jitter_seconds)
                if self.jitter_seconds > 0
                else 0.0
            )
            gap_seconds = None if previous is None else max(0.0, now - previous)
            wait_seconds = 0.0
            if previous is not None:
                earliest = previous + self.fresh_chat_min_interval_seconds + jitter
                wait_seconds = max(0.0, earliest - now)

        if wait_seconds > 0:
            self._sleep(wait_seconds)

        with self._lock:
            self._last_fresh_attempt_at = self._clock()
            return {
                "fresh_chat": True,
                "fresh_chat_gap_seconds": (
                    None if gap_seconds is None else round(gap_seconds, 3)
                ),
                "fresh_chat_wait_seconds": round(wait_seconds, 3),
                "fresh_chat_jitter_seconds": round(jitter, 3),
            }

    def finish_task(self, task_type: str, result: dict | None) -> dict:
        if task_type not in CHATGPT_WRITE_TASK_TYPES:
            return {}

        category = throttle_category(result)
        now = self._clock()
        with self._lock:
            metadata: dict[str, object] = {}
            try:
                if category is not None:
                    index = min(self._throttle_streak, len(self.backoff_seconds) - 1)
                    base = self.backoff_seconds[index]
                    jitter = (
                        self._jitter(0.0, self.jitter_seconds)
                        if self.jitter_seconds > 0
                        else 0.0
                    )
                    delay = base + jitter
                    self._throttle_streak += 1
                    self._last_throttle_category = category
                    self._cooldown_until = max(self._cooldown_until, now + delay)
                    metadata.update({
                        "throttle_category": category,
                        "backoff_seconds": round(delay, 3),
                        "throttle_streak": self._throttle_streak,
                    })
                elif isinstance(result, dict) and result.get("success"):
                    self._throttle_streak = 0
                    self._last_throttle_category = None
                    self._cooldown_until = 0.0
                    metadata.update({
                        "throttle_category": None,
                        "backoff_seconds": 0.0,
                        "throttle_streak": 0,
                    })
                return metadata
            finally:
                self._active_write = False

    def snapshot(self) -> dict:
        with self._lock:
            now = self._clock()
            return {
                "active_write": self._active_write,
                "fresh_chat_min_interval_seconds": self.fresh_chat_min_interval_seconds,
                "jitter_seconds": self.jitter_seconds,
                "backoff_seconds": list(self.backoff_seconds),
                "cooldown_remaining_seconds": round(
                    max(0.0, self._cooldown_until - now), 3
                ),
                "throttle_streak": self._throttle_streak,
                "last_throttle_category": self._last_throttle_category,
                "fresh_chat_seen": self._last_fresh_attempt_at is not None,
            }
