# -*- coding: utf-8 -*-
"""
Circuit Breaker Implementation
"""

import time
import threading
from enum import Enum
from typing import Dict, Optional


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject all requests
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: int = 300,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls: int = 0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if cooldown has passed
                if (
                    self._last_failure_time is not None
                    and time.time() - self._last_failure_time >= self.cooldown_seconds
                ):
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def is_available(self) -> bool:
        """Check if requests can pass through."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self, error: Optional[str] = None) -> None:
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def record_inconclusive(self) -> None:
        """Record an inconclusive result (e.g., empty response)."""
        with self._lock:
            # Treat as partial failure, don't reset but don't increment either
            pass

    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        with self._lock:
            current_state = self.state

            if current_state == CircuitState.CLOSED:
                return True

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False  # OPEN state