import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path('shared/framework/hermes-agent').resolve()))
from shared.assistant.master_turn import SystemInteractionRuntime


@pytest.mark.parametrize('raises', [False, True])
def test_provider_outliving_outer_turn_retains_slot_until_exit(raises):
    from agent.request_threads import start_owned_thread
    release, started = threading.Event(), threading.Event()
    class Agent:
        def run_conversation(self, **kwargs):
            def provider():
                started.set()
                release.wait(5)
            start_owned_thread(threading.Thread(target=provider, daemon=True))
            assert started.wait(1)
            if raises:
                raise RuntimeError('private provider details')
            return {'final_response': '{"message":"ok"}'}
    runtime = SystemInteractionRuntime(lambda sid: Agent(),
        Path('skills/system-interaction-core/SKILL.md'), capacity=1, timeout=.05)
    payload = {'query': 'help', 'session_id': 'owned'}
    try:
        with pytest.raises(HTTPException) as error:
            runtime.respond(payload)
        assert error.value.status_code == 504
        assert runtime._active == 1
        assert next(iter(runtime._sessions.values()))['busy']
        for session in ('owned', 'other'):
            with pytest.raises(HTTPException) as busy:
                runtime.respond(dict(payload, session_id=session))
            assert busy.value.status_code == 409
    finally:
        release.set()
    deadline = time.monotonic() + 2
    while runtime._active and time.monotonic() < deadline:
        threading.Event().wait(.005)
    assert runtime._active == 0


def test_unowned_thread_start_does_not_wait():
    from agent.request_threads import start_owned_thread
    release = threading.Event()
    thread = threading.Thread(target=lambda: release.wait(2), daemon=True)
    try:
        start_owned_thread(thread)
        assert thread.is_alive()
    finally:
        release.set()
        thread.join(1)


def test_scope_drains_descendants_and_restores_context_after_exception():
    from agent.request_threads import RequestThreadScope, start_owned_thread
    release, child_started, drained = (threading.Event() for _ in range(3))
    def child():
        child_started.set()
        release.wait(3)
    def parent():
        start_owned_thread(threading.Thread(target=child, daemon=True))
    def owner():
        try:
            with RequestThreadScope():
                start_owned_thread(threading.Thread(target=parent, daemon=True))
                assert child_started.wait(1)
                raise ValueError('scope failure')
        except ValueError:
            drained.set()
    worker = threading.Thread(target=owner, daemon=True)
    worker.start()
    try:
        assert child_started.wait(1)
        assert not drained.wait(.03)
        # No ownership leaks onto the unrelated calling thread.
        plain = threading.Thread(target=lambda: None)
        start_owned_thread(plain)
        plain.join(1)
    finally:
        release.set()
        worker.join(2)
    assert drained.is_set()
