"""Retry policy module.

This file is intentionally verbose for demo purposes.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")

@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retries."""
    max_attempts: int = 5
    base_delay_s: float = 0.25
    max_delay_s: float = 4.0
    jitter: bool = True

def compute_delay(attempt: int, policy: RetryPolicy) -> float:
    """Exponential backoff with optional jitter."""
    delay = min(policy.max_delay_s, policy.base_delay_s * (2 ** (attempt - 1)))
    if policy.jitter:
        delay = delay * (0.7 + 0.6 * random.random())
    return delay

def with_retries(fn: Callable[[], T], policy: RetryPolicy) -> T:
    """Execute fn with retries.

    Behavior:
    - retries up to policy.max_attempts
    - sleeps between attempts using compute_delay
    - raises the last exception if all attempts fail
    """
    last_err: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt >= policy.max_attempts:
                break
            time.sleep(compute_delay(attempt, policy))
    assert last_err is not None
    raise last_err

DEFAULT_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay_s=0.25,
    max_delay_s=4.0,
    jitter=True,
)
