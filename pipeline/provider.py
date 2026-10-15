"""Process-wide API admission and spend bounds, shared by authoring and solvers."""
from __future__ import annotations
import contextlib
import json
import math
import random
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import os
import threading
import time


class ProviderBudgetExhausted(BaseException):
    """The process-wide request cap is spent: stop the run, loudly.

    A `BaseException`, deliberately, like `KeyboardInterrupt`. Every rollout and
    review loop catches `Exception` and records it as a void or an unverified
    verdict, so an ordinary exception here turned budget exhaustion into a
    stream of voids that looked like results. This one passes through those
    handlers and ends the run instead.
    """


EXHAUSTED = "provider request budget exhausted; run stopped, no evidence recorded"


class RequestBudget:
    """Concurrency and a request-count spend cap. No wall-clock deadline.

    There used to be one (`ARENA_API_WALL_SECONDS`, 4 hours), and past it every
    rollout became a void: every screening episode after hour four of a long
    batch was unverified. POLICY runs calibration with no turn or time limits, so time is
    not a budget here. Exhaustion of the request cap raises
    `ProviderBudgetExhausted`, which stops the run rather than voiding it.
    """

    def __init__(self, concurrency=8, max_requests=2500):
        if concurrency < 1 or max_requests < 1:
            raise ValueError("provider budget values must be positive")
        self.semaphore = threading.BoundedSemaphore(concurrency)
        self.lock = threading.Lock()
        self.max_requests = max_requests
        self.started = None
        self.requests = 0

    @contextlib.contextmanager
    def slot(self):
        with self.semaphore:
            with self.lock:
                if self.started is None:
                    self.started = time.monotonic()
                if self.requests >= self.max_requests:
                    raise ProviderBudgetExhausted(EXHAUSTED)
                self.requests += 1
            yield

    def stats(self):
        with self.lock:
            return {"requests": self.requests, "max_requests": self.max_requests,
                    "elapsed_seconds": round(time.monotonic() - self.started, 2) if self.started else 0}


from .config import MAX_API_REQUESTS, MAX_PROVIDER_CONCURRENCY
GLOBAL = RequestBudget(int(os.environ.get("ARENA_PROVIDER_CONCURRENCY", str(MAX_PROVIDER_CONCURRENCY))),
                       int(os.environ.get("ARENA_MAX_API_REQUESTS", str(MAX_API_REQUESTS))))
request_slot = GLOBAL.slot


_NONRETRYABLE_QUOTA_CODES = frozenset({
    'insufficient_quota', 'billing_hard_limit_reached',
    'billing_not_active', 'organization_spend_limit_exceeded',
    'project_spend_limit_exceeded', 'organization_usage_limit_exceeded',
})


MAX_RETRY_SLEEP_S = 120.0


def _retry_delay(headers, attempt: int) -> float | None:
    """Respect the server's minimum delay, or defer beyond the wait allowance."""
    delay = min(2 ** attempt, 32) + random.random()
    value = (headers or {}).get('Retry-After')
    if value is None:
        return delay
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            seconds = (date - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return delay
    if math.isfinite(seconds) and seconds >= 0:
        return max(delay, seconds) if seconds <= MAX_RETRY_SLEEP_S else None
    return delay


def _http_failure(exc, attempt: int):
    # Error bodies can quote prompts. Read only enough to classify known quota
    # codes, and never put provider prose into logs or retained trial errors.
    try:
        payload = json.loads(exc.read(8192))
    except (ValueError, TypeError, UnicodeDecodeError):
        payload = {}
    error = payload.get('error') if isinstance(payload, dict) else None
    code = error.get('code') if isinstance(error, dict) else None
    quota = isinstance(code, str) and code in _NONRETRYABLE_QUOTA_CODES
    message = f'HTTP {exc.code}: provider request failed'
    if quota:
        message += ' (quota or spend limit; retry cannot restore access)'
    retryable = not quota and (exc.code in (408, 409, 429) or 500 <= exc.code < 600)
    delay = _retry_delay(exc.headers, attempt) if retryable else None
    if retryable and delay is None:
        message += ' (server retry delay exceeds wait allowance; continuation deferred, not a task failure)'
    return RuntimeError(message), delay


def _transport_observer(provider="anthropic"):
    """Optional payload-free telemetry; observation failures cannot change a run."""
    filename = os.environ.get('ARENA_TRANSPORT_OBSERVATIONS')
    request_id, started = uuid.uuid4().hex, time.monotonic()
    def observe(stage, **metadata):
        if not filename:
            return
        row = {'provider': provider, 'request_id': request_id, 'stage': stage,
               'at': datetime.now(timezone.utc).isoformat(),
               'elapsed_s': round(time.monotonic() - started, 3), **metadata}
        try:
            fd = os.open(filename, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, (json.dumps(row) + '\n').encode())
            finally:
                os.close(fd)
        except OSError:
            pass
    return observe
