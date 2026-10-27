# Clean Hermes Branch and Frontend Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Hermes phase-one branch from the authoritative local `main`, preserve the paper-based branch as a backup, and restore a reproducible frontend dependency and test baseline.

**Architecture:** Preserve history before changing branch topology, then cherry-pick only the reviewed phase-one system commit and this plan onto a clean branch. Remove generated frontend dependencies and build output from Git tracking, recreate dependencies strictly from `package-lock.json`, and verify both frontend and Python suites before restarting services.

**Tech Stack:** Git, Node.js/npm, Vue 3, TypeScript, Vitest, Vite, Python 3.12, pytest

---

### Task 1: Preserve and rebuild the development branch

**Files:**
- Preserve: all files reachable from `codex/hermes-phase1-hardening`
- Create branch: `backup/hermes-phase1-paper-base`
- Recreate branch: `codex/hermes-phase1-hardening` from local `main`

- [ ] Stop application services that hold tracked runtime files open.
- [ ] Restore generated Vite cache changes and preserve unrelated local-only files.
- [ ] Rename the existing paper-based branch to `backup/hermes-phase1-paper-base`.
- [ ] Create `codex/hermes-phase1-hardening` from local `main`.
- [ ] Cherry-pick phase-one commit `3ee69d9` and this migration-plan commit.
- [ ] Confirm the new branch history contains no paper-only commits.

### Task 2: Remove generated frontend artifacts from version control

**Files:**
- Modify: `.gitignore`
- Remove from Git index: `frontend/node_modules/**`
- Remove from Git index: `frontend/dist/**`

- [ ] Add `/frontend/node_modules/` and `/frontend/dist/` to `.gitignore`.
- [ ] Remove both generated directories from Git tracking.
- [ ] Commit only ignore rules and index removals.
- [ ] Confirm `git ls-files` reports zero files in both directories.

### Task 3: Restore and verify the frontend toolchain

**Files:**
- Verify: `frontend/package.json`
- Verify: `frontend/package-lock.json`

- [ ] Remove the stale local dependency directory after resolving its absolute project path.
- [ ] Run `npm ci` in `frontend/` and require exit code 0.
- [ ] Run `npm ls --depth=0` and require no missing or invalid direct dependencies.
- [ ] Run `npm run type-check` and require exit code 0.
- [ ] Run `npm test -- --run` and require zero failed tests.
- [ ] Run `npm run build` and require exit code 0.

### Task 4: Verify the migrated system and restore services

**Files:**
- Verify: phase-one files listed by commit `3ee69d9`

- [ ] Run `python -m pytest -q tests backend/tests` and require zero failures.
- [ ] Run `git diff --check` and require no whitespace errors.
- [ ] Confirm only intended commits and local-only ignored artifacts remain.
- [ ] Restart InfluxDB, simulator, Agent, backend, and frontend from `E:\project\Ecological_env`.
- [ ] Probe ports 8086, 8642, 8000, and 5173 and require HTTP 200.
