"""State guard preventing work from overlapping a timed-out agent turn."""
import threading


class AgentTurnGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = "idle"
        self._worker_done: threading.Event | None = None
        self._needs_agent_rebuild = False

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def needs_agent_rebuild(self) -> bool:
        with self._lock:
            return self._needs_agent_rebuild

    def try_begin(self) -> bool:
        with self._lock:
            if self._state != "idle" or self._needs_agent_rebuild:
                return False
            self._state = "running"
            return True

    def finish(self) -> None:
        with self._lock:
            if self._state == "running":
                self._state = "idle"

    def mark_timed_out(self, worker_done: threading.Event) -> None:
        with self._lock:
            self._worker_done = worker_done
            self._state = "quarantined"

    def wait_for_recovery(self, timeout: float = 0.0) -> bool:
        with self._lock:
            event = self._worker_done
            state = self._state
        if state != "quarantined" or event is None or not event.wait(timeout):
            return False
        with self._lock:
            self._needs_agent_rebuild = True
        return True

    def mark_agent_rebuilt(self) -> None:
        with self._lock:
            self._worker_done = None
            self._needs_agent_rebuild = False
            self._state = "idle"

