import threading

from backend.services.agent_turn_guard import AgentTurnGuard


def test_timeout_quarantines_until_worker_finishes():
    guard = AgentTurnGuard()
    worker_done = threading.Event()

    assert guard.try_begin() is True
    guard.mark_timed_out(worker_done)
    assert guard.try_begin() is False
    assert guard.state == "quarantined"

    worker_done.set()
    assert guard.wait_for_recovery(timeout=0.1) is True
    assert guard.needs_agent_rebuild is True


def test_rebuild_acknowledgement_returns_guard_to_idle():
    guard = AgentTurnGuard()
    worker_done = threading.Event()
    guard.try_begin()
    guard.mark_timed_out(worker_done)
    worker_done.set()
    assert guard.wait_for_recovery(timeout=0.1) is True

    guard.mark_agent_rebuilt()

    assert guard.state == "idle"
    assert guard.needs_agent_rebuild is False
    assert guard.try_begin() is True
    guard.finish()
