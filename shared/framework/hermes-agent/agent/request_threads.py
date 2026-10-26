"""Opt-in ownership of provider threads for bounded request lifetimes."""
from contextvars import ContextVar, copy_context
from threading import Lock


_owner = ContextVar('provider_request_thread_owner', default=None)


class RequestThreadScope:
    """Keep the owning worker alive until its provider threads really exit."""

    def __init__(self):
        self._threads = set()
        self._lock = Lock()

    def __enter__(self):
        self._token = _owner.set(self)
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            while True:
                with self._lock:
                    threads = tuple(self._threads)
                if not threads:
                    break
                for thread in threads:
                    thread.join()
                with self._lock:
                    self._threads.difference_update(threads)
        finally:
            _owner.reset(self._token)

    def start(self, thread):
        # Register before starting; a child can itself start owned descendants.
        context = copy_context()
        run = thread.run
        thread.run = lambda: context.run(run)
        with self._lock:
            self._threads.add(thread)
            try:
                thread.start()
            except BaseException:
                self._threads.remove(thread)
                thread.run = run
                raise


def start_owned_thread(thread):
    """Start normally unless the caller opted into request ownership."""
    owner = _owner.get()
    if owner is None:
        thread.start()
    else:
        owner.start(thread)
