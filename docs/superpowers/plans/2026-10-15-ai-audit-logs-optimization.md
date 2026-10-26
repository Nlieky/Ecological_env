# AI Assistant, Audit Search, and Logs Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AI conversations independently runnable and visible, make audit search reliably discover partial titles, and reorganize logs into an operationally useful filtered stream.

**Architecture:** The chat store will own one runtime object per conversation instead of one global stream. Audit search will normalize and tokenize input before server-side filtering. Logs will keep the existing storage tables but add one aggregated query contract consumed by a scan-friendly Vue view.

**Tech Stack:** Vue 3, Pinia, TypeScript, Vitest, FastAPI, SQLAlchemy, Pytest.

---

### Task 1: Conversation-scoped runtime state

**Files:**
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/components/aiops/ConversationList.vue`
- Modify: `frontend/src/components/aiops/ChatComposer.vue`
- Test: `frontend/src/stores/__tests__/chat.spec.ts`

- [ ] Add failing store tests proving that switching conversations does not abort an existing stream, two conversations keep separate message buffers, and cancellation targets one conversation.
- [ ] Run `npm run test -- --run src/stores/__tests__/chat.spec.ts` from `frontend`; expect the new assertions to fail against the global runtime implementation.
- [ ] Introduce `ConversationRuntime` keyed by conversation ID, current-runtime computed accessors, and conversation-scoped stream callbacks/controllers.
- [ ] Update the conversation list to render `queued/running/failed/completed` indicators and update the composer to disable only for the current conversation.
- [ ] Re-run the focused store test and add component assertions for status labels; expect all focused tests to pass.

### Task 2: Normalized audit search and themed controls

**Files:**
- Modify: `backend/services/conversation_service.py`
- Modify: `frontend/src/composables/useAuditList.ts`
- Modify: `frontend/src/views/AgentAuditView.vue`
- Test: `backend/tests/test_conversation_retrieval.py`
- Test: `frontend/src/composables/__tests__/useAuditList.spec.ts`
- Test: `frontend/src/views/__tests__/AgentAuditView.spec.ts`

- [ ] Add failing backend tests for trimmed multi-keyword partial matches and frontend tests for debounced input, page reset, clear, result count, and stale-response protection.
- [ ] Run the focused Pytest and Vitest files; expect failures for missing normalization/debounce behavior.
- [ ] Normalize whitespace, split search terms, and require every term to match title or conversation ID; retain escaped substring matching.
- [ ] Add a 300 ms debounced search API to the composable and replace native audit controls with themed input, clear/search actions, loading and empty feedback.
- [ ] Re-run focused tests; expect all to pass.

### Task 3: Aggregated log query contract

**Files:**
- Modify: `backend/api/routes/logs.py`
- Modify: `frontend/src/api/modules/logs.ts`
- Modify: `frontend/src/api/types/api.types.ts`
- Test: `backend/tests/test_logs_query.py`

- [ ] Add failing API/service tests for aggregated results, severity derivation, keyword/module/time filters, slow-call classification, and pagination.
- [ ] Run `pytest backend/tests/test_logs_query.py -q`; expect failures because the aggregate contract does not exist.
- [ ] Add an `all` query mode and normalized fields (`level`, `slow`, `session_id`) while preserving existing type-specific requests.
- [ ] Extend frontend types and API parameters for the normalized contract.
- [ ] Re-run the focused backend test; expect it to pass.

### Task 4: Logs operational workbench

**Files:**
- Modify: `frontend/src/views/LogsView.vue`
- Test: `frontend/src/views/__tests__/navigation.spec.ts`
- Test: `frontend/src/views/__tests__/LogsView.spec.ts`

- [ ] Add failing component tests for summary filters, module/time/search query forwarding, expandable context, loading/error/empty states, and trace links.
- [ ] Run focused Vitest files; expect the new workbench assertions to fail against the table view.
- [ ] Replace the table with summary filters, toolbar, structured log rows, details disclosure and pagination, using the existing application tokens.
- [ ] Re-run focused view tests; expect all to pass.

### Task 5: Integration verification

**Files:**
- Modify only if verification exposes a regression.

- [ ] Run focused frontend tests for chat, audit and logs.
- [ ] Run focused backend tests for conversations and logs.
- [ ] Run full frontend TypeScript check and production build.
- [ ] Run the relevant backend/system regression set.
- [ ] Start or reload the frontend/backend services, verify health endpoints, and manually exercise two chat sessions, partial audit search, and log filters.
- [ ] Review `git diff` to confirm no unrelated user changes were overwritten and report exact verification evidence.
