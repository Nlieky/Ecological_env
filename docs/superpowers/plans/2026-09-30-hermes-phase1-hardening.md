# Hermes Phase 1 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate silent stale-result reuse, expose stale monitoring data, centralize subagent identities, and quarantine timed-out agent turns.

**Architecture:** Introduce two small contract modules: a canonical subagent registry shared by the caller and subprocess entry, and deterministic helpers for result freshness and query execution state. Preserve carried results as upstream context, but delete the target subagent's prior output before every invocation so a failed run cannot be mistaken for a current result. Mark relative-window data with actual bounds and freshness metadata. After a wall timeout, reject new work until the orphan worker exits and rebuild the shared agent before reuse.

**Tech Stack:** Python 3.12, FastAPI, Hermes Agent, pytest, pandas.

---

### Task 1: Canonical subagent registry and result-generation isolation

**Files:**
- Create: `skills/orchestrator-core/scripts/subagent_registry.py`
- Modify: `skills/orchestrator-core/scripts/call_subagent.py`
- Modify: `skills/orchestrator-core/scripts/subagent_entry.py`
- Test: `tests/system/test_subagent_contract.py`

- [ ] Write tests asserting all aliases resolve to a canonical name/result file and that a target result is removed before a subprocess invocation.
- [ ] Run `python -m pytest tests/system/test_subagent_contract.py -q` and confirm the tests fail because the registry and cleanup API do not exist.
- [ ] Implement `resolve_subagent(name)`, canonical definitions, aliases, and `prepare_result_target(session_dir, filename)`; pass only the canonical name to the child process.
- [ ] Run the focused test and confirm it passes.
- [ ] Review the diff for duplicated maps, unsafe path handling, and compatibility with the four canonical names.

### Task 2: Monitoring-data freshness contract

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py`
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md`
- Test: `tests/system/test_data_freshness.py`

- [ ] Write tests for fresh relative data, stale relative data, explicit historical ranges, and empty datasets using a pure `assess_data_freshness` helper.
- [ ] Run `python -m pytest tests/system/test_data_freshness.py -q` and confirm failure because the helper is absent.
- [ ] Implement actual data bounds, lag hours, `is_stale`, and a structured warning for relative requests; explicit historical ranges must never be mislabeled stale merely because they are old.
- [ ] Add the freshness object to result metadata and teach the skill to disclose stale data instead of calling it current.
- [ ] Run focused tests and review timezone/empty-data edge cases.

### Task 3: Timeout quarantine and safe recovery

**Files:**
- Create: `backend/services/agent_turn_guard.py`
- Modify: `scripts/start_agent.py`
- Test: `backend/tests/test_agent_turn_guard.py`

- [ ] Write tests showing that a timed-out worker leaves the guard quarantined, new work is rejected while it remains alive, and recovery becomes available only after it exits.
- [ ] Run `python -m pytest backend/tests/test_agent_turn_guard.py -q` and confirm the missing module failure.
- [ ] Implement a lock-protected `AgentTurnGuard` with explicit running/quarantined/idle states and a completion event.
- [ ] Integrate it into both blocking and streaming query paths; on timeout, keep the service quarantined and rebuild the shared AIAgent before the next accepted query.
- [ ] Run focused tests and verify no request can overlap an orphaned conversation worker.

### Task 4: Security pruning, regression, and documentation alignment

**Files:**
- Modify: `skills/orchestrator-core/scripts/subagent_entry.py`
- Modify: `workspace/AGENTS.md`
- Modify: `workspace/TOOLS.md`
- Modify: `README.md`
- Test: `tests/system/test_subagent_contract.py`

- [ ] Add a failing assertion that the subagent tool list excludes `skill_manage` while retaining `skill_view`, `skills_list`, and terminal execution.
- [ ] Implement explicit post-initialization tool pruning and refresh `valid_tool_names`.
- [ ] Correct stale `workspace/skills/` documentation paths to root `skills/`.
- [ ] Run focused tests, then `python -m pytest backend/tests tests/system tests/events tests/knowledge_graph tests/rule_reasoning -q`.
- [ ] Run Python compilation checks on every modified module and inspect `git diff --check`.
- [ ] Review all changes against the four phase-one requirements and record any remaining external-service limitations.
