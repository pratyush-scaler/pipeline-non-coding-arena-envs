"""Share native trial capacity across simultaneous task/model campaigns."""
from collections import deque
from contextlib import contextmanager
import os
import threading


class NativeCapacity:
    def __init__(self, limit):
        if type(limit) is not int or limit < 1:
            raise ValueError('Native episode capacity must be positive')
        self.limit = limit
        self.active = self.peak = 0
        self.condition = threading.Condition()
        self.waiting = deque()

    @contextmanager
    def reserve(self, requested):
        if type(requested) is not int or requested < 1:
            raise ValueError('Requested episode slots must be positive')
        ticket = object()
        with self.condition:
            self.waiting.append(ticket)
            self.condition.notify_all()
            try:
                self.condition.wait_for(lambda: self.waiting[0] is ticket and self.active < self.limit)
                granted = min(requested, self.limit - self.active)
                self.active += granted
                self.peak = max(self.peak, self.active)
            finally:
                self.waiting.remove(ticket)
                self.condition.notify_all()
        try:
            yield granted
        finally:
            with self.condition:
                self.active -= granted
                self.condition.notify_all()

    def stats(self):
        with self.condition:
            return {'limit': self.limit, 'reserved': self.active, 'peak_reserved': self.peak,
                    'waiting_campaigns': len(self.waiting)}


NATIVE_CAPACITY = NativeCapacity(int(os.environ.get('ARENA_NATIVE_CONCURRENCY', '16')))
