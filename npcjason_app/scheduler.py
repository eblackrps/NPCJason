from __future__ import annotations

from dataclasses import dataclass
import queue
import threading
from typing import Callable, Dict, Optional


@dataclass
class ScheduledJob:
    name: str
    owner: str
    repeating: bool
    default_delay_ms: int
    error_delay_ms: int
    after_id: Optional[str] = None
    run_count: int = 0
    failure_count: int = 0
    last_delay_ms: Optional[int] = None
    running: bool = False


class ManagedTkScheduler:
    def __init__(self, root, logger=None, dispatch_interval_ms=40, max_dispatch_batch=64, dispatch_warn_depth=128):
        self.root = root
        self.logger = logger
        self.dispatch_interval_ms = max(10, int(dispatch_interval_ms))
        self.max_dispatch_batch = max(1, int(max_dispatch_batch))
        self.dispatch_warn_depth = max(8, int(dispatch_warn_depth))
        self._main_thread_id = threading.get_ident()
        self._jobs: Dict[str, ScheduledJob] = {}
        self._dispatch_queue = queue.Queue()
        self._shutdown = False
        self._dispatch_warning_emitted = False

    def start(self):
        self.schedule_loop(
            "_ui_dispatch",
            self._drain_dispatch_queue,
            initial_delay_ms=0,
            default_delay_ms=self.dispatch_interval_ms,
            owner="scheduler",
        )

    def dispatch(self, callback: Callable, *args, **kwargs):
        if self._shutdown:
            return
        self._dispatch_queue.put((callback, args, kwargs))
        queue_depth = self._dispatch_queue.qsize()
        if queue_depth >= self.dispatch_warn_depth and not self._dispatch_warning_emitted:
            self._dispatch_warning_emitted = True
            self._log("warning", f"Dispatch queue depth is high ({queue_depth})")

    def on_ui_thread(self):
        return threading.get_ident() == self._main_thread_id

    def schedule(self, name, delay_ms, callback, owner="app"):
        replaced = self.cancel(name)
        job = ScheduledJob(
            name=name,
            owner=owner,
            repeating=False,
            default_delay_ms=max(0, int(delay_ms)),
            error_delay_ms=max(50, int(delay_ms) or 50),
        )
        self._jobs[name] = job
        self._log("info", f"Scheduled job '{name}' (owner={owner}, delay_ms={job.default_delay_ms}, replaced={replaced})")

        def runner():
            if self._shutdown or self._jobs.get(name) is not job:
                return
            self._jobs.pop(name, None)
            try:
                job.running = True
                callback()
                job.run_count += 1
            except Exception:
                job.failure_count += 1
                self._log_exception(f"Scheduled callback '{name}' failed")
            finally:
                job.running = False

        job.after_id = self.root.after(job.default_delay_ms, runner)
        return job

    def schedule_loop(
        self,
        name,
        callback,
        initial_delay_ms=0,
        default_delay_ms=1000,
        error_delay_ms=None,
        owner="app",
    ):
        replaced = self.cancel(name)
        job = ScheduledJob(
            name=name,
            owner=owner,
            repeating=True,
            default_delay_ms=max(1, int(default_delay_ms)),
            error_delay_ms=max(50, int(error_delay_ms or default_delay_ms or 50)),
        )
        self._jobs[name] = job
        self._log(
            "info",
            f"Scheduled loop '{name}' (owner={owner}, initial_delay_ms={int(initial_delay_ms)}, default_delay_ms={job.default_delay_ms}, replaced={replaced})",
        )

        def runner():
            if self._shutdown or self._jobs.get(name) is not job:
                return
            if job.running:
                job.failure_count += 1
                self._log("warning", f"Loop '{name}' was invoked while already running; delaying retry")
                job.after_id = self.root.after(job.error_delay_ms, runner)
                return
            try:
                job.running = True
                next_delay = callback()
                job.run_count += 1
            except Exception:
                job.failure_count += 1
                self._log_exception(f"Loop callback '{name}' failed")
                next_delay = job.error_delay_ms
            finally:
                job.running = False
            if self._shutdown or self._jobs.get(name) is not job:
                return
            if next_delay is None:
                self._jobs.pop(name, None)
                job.after_id = None
                self._log("info", f"Loop '{name}' completed without reschedule")
                return
            delay = max(1, int(next_delay))
            job.last_delay_ms = delay
            job.after_id = self.root.after(delay, runner)

        job.after_id = self.root.after(max(0, int(initial_delay_ms)), runner)
        return job

    def cancel(self, name):
        job = self._jobs.pop(name, None)
        if not job or not job.after_id:
            return False
        try:
            self.root.after_cancel(job.after_id)
        except Exception:
            self._log_exception(f"Failed to cancel scheduled job '{name}'")
        else:
            self._log("info", f"Canceled scheduled job '{name}'")
        return True

    def cancel_owner(self, owner):
        job_names = [name for name, job in self._jobs.items() if job.owner == owner]
        for name in job_names:
            self.cancel(name)

    def cancel_all(self):
        for name in list(self._jobs):
            self.cancel(name)

    def shutdown(self):
        self._shutdown = True
        self._log("info", "Scheduler shutdown requested")
        self.cancel_all()
        while True:
            try:
                self._dispatch_queue.get_nowait()
            except queue.Empty:
                break

    def describe_jobs(self):
        description = []
        for name, job in sorted(self._jobs.items()):
            description.append(
                {
                    "name": name,
                    "owner": job.owner,
                    "repeating": job.repeating,
                    "default_delay_ms": job.default_delay_ms,
                    "run_count": job.run_count,
                    "failure_count": job.failure_count,
                    "last_delay_ms": job.last_delay_ms,
                }
            )
        return description

    def _drain_dispatch_queue(self):
        processed = 0
        while processed < self.max_dispatch_batch:
            try:
                callback, args, kwargs = self._dispatch_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args, **kwargs)
            except Exception:
                callback_name = getattr(callback, "__name__", repr(callback))
                self._log_exception(f"Dispatched callback '{callback_name}' failed")
            processed += 1
        if self._dispatch_queue.qsize() < self.dispatch_warn_depth:
            self._dispatch_warning_emitted = False
        return self.dispatch_interval_ms

    def _log_exception(self, message):
        if self.logger and hasattr(self.logger, "exception"):
            self.logger.exception(message)

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method("[scheduler] " + str(message))
