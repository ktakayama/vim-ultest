import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from queue import Empty, PriorityQueue
from threading import Thread
from typing import Callable, Coroutine, List, Optional, Union


class JobPriority(int, Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1


@dataclass(order=True)
class PrioritizedJob:
    priority: Union[JobPriority, int]
    func: Callable[[], Coroutine] = field(compare=False)


class JobManager:
    def __init__(self, num_threads: int = 0):
        if not num_threads:
            os_count = os.cpu_count()
            if os_count is not None:
                num_threads = max(1, os_count - 1)
            else:
                num_threads = 4
        num_threads = 3
        self._queue: PriorityQueue[PrioritizedJob] = PriorityQueue()
        self._threads: List[Thread] = []
        self._running = True
        self._num_threads = num_threads
        self._start_workers(num_threads)
        logging.info(f"Using {num_threads} workers")

    def set_threads(self, num: int):
        self._start_workers(num)

    def run(self, func: Callable[[], Coroutine], priority: Union[int, JobPriority]):
        self._queue.put(PrioritizedJob(priority=priority, func=func))

    def clear_jobs(self):
        self._running = False
        while not self._queue.empty():
            try:
                self._queue.get()
            except Empty:
                pass
        self._running = True

    def _stop_workers(self, timeout: Optional[float] = None):
        self._running = False
        for thread in self._threads:
            thread.join(timeout)

    def _start_workers(self, max_threads):
        self._stop_workers()
        self._running = True
        for _ in range(max_threads):
            thread = Thread(target=self._start_worker, daemon=True)
            thread.start()
            self._threads.append(thread)

    def _start_worker(self):
        async def work():
            while self._running:
                try:
                    job = self._queue.get()
                    await job.func()
                except Exception as e:
                    logging.exception(e)

        asyncio.run(work())
