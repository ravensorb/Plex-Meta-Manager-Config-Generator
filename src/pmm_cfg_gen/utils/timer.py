#!/usr/bin/env python3
#######################################################################
# timer.py

import time
import datetime
from contextlib import ContextDecorator
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Optional
from pmm_cfg_gen.utils.time_span import timespan

#######################################################################

class timer_exception(Exception):
    """A custom exception used to report errors in use of Timer class"""

@dataclass
class timer(ContextDecorator):
    """Time your code using a class, context manager, or decorator"""

    timers: ClassVar[Dict[str, float]] = {}
    name: Optional[str] = None
    text: str = "Elapsed time: {:0.4f} seconds"
    logger: Optional[Callable[[str], None]] = None

    _start_time: float = field(default=0, init=True, repr=False)
    _end_time: float = field(default=0, init=True, repr=False)
    _elapsed_time: timespan = field(default=Any, init=False, repr=False)
    _is_running: bool = field(default=False, init=True, repr=False)

    def __post_init__(self) -> None:
        """Initialization: add timer to dict of timers"""
        if self.name:
            self.timers.setdefault(self.name, 0)

    def start(self) -> None:
        """Start a new timer"""
        if self._is_running:
            raise timer_exception(f"Timer is running. Use .stop() to stop it")

        self._is_running = True
        self._start_time = time.perf_counter()

    def stop(self) -> None:
        """Stop the timer, and report the elapsed time"""
        if not self._is_running:
            raise timer_exception(f"Timer is not running. Use .start() to start it")

        # Calculate elapsed time
        self._end_time = time.perf_counter()
        self._elapsed_time = timespan(seconds=(self._end_time - self._start_time))
        self._is_running = False

        # Report elapsed time
        if self.logger:
            self.logger(self.text.format(self._elapsed_time))
        if self.name:
            self.timers[self.name] += self._elapsed_time.total_seconds

    @property
    def elapsed_time(self) -> float:
        return self._elapsed_time.total_seconds

    @property
    def elapsed_time_ts(self) -> timespan:
        return self._elapsed_time
    
    def __enter__(self) -> "timer":
        """Start a new timer as a context manager"""
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Stop the context manager timer"""
        self.stop()

    def to_dict(self):
        return { "start": self._start_time, "end": self._end_time, "elapsed": self._elapsed_time.to_dict() }