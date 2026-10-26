# Batch 2 Existing Function Optimization

> Execute with subagent-driven-development and test-driven-development, with spec then quality review for each task. User approved the design in conversation. Original checkout only; preserve Batch 1 changes and local settings. Do not commit the mixed working tree, push, merge or create worktrees.

**Goal:** Reliable existing workflows, measurable Agent latency and actionable retrieval/navigation.

**Architecture:** Retain serialized shared Agent execution. Measure monotonic elapsed time without new queues or tracing infrastructure. Existing database/API contracts remain compatible; pagination/search are additive. Frontend asynchronous writes must belong to the current request and selection. Failed writes must not masquerade as saved state.

**Tech Stack:** Vue/Pinia/TypeScript/Vitest; FastAPI/pytest/InfluxDB.

## Approved design and boundaries

AI: handle disconnected, busy and timed-out streams, preserve partial text, prevent session cross-talk, report total and subagent durations. Audit: searchable paginated conversations and session links. Events: paginated filters, confirmed status changes, independent relation errors. Configuration: distinguish saved values from effective runtime and restart/next-turn behavior. Graph/logs: reliable existing deep links and failure states.

Excluded: authentication, expert approval workflow, parallel Agent redesign, report exports, new event sources, Prometheus/Grafana and Batch 3 layout changes.

## Task 1: Stream lifecycle and measured latency

Files: frontend/src/api/modules/query.ts; frontend/src/stores/chat.ts; frontend/src/components/aiops/ChatMessage.vue; scripts/start_agent.py; skills/orchestrator-core/scripts/tool_registration.py; focused tests under frontend/src/api/modules/__tests__, frontend/src/stores/__tests__, tests/system.

- [x] RED: stream EOF without terminal event calls error once; CRLF/chunked frames parse; abort settles; HTTP error includes safe detail; completion releases reader; partial output survives failure; stale session callbacks ignored; deferred conversation selections do not overwrite current; timings use nonnegative elapsed values. Implementer observed initial 7 frontend failures, 3 Agent failures, 3 proxy failures and additional timing/failure regressions.
- [x] Focused root verification: frontend query.spec.ts/chat.spec.ts 12 passed; backend test_stream_lifecycle.py/test_stream_proxy.py 8 passed. Browser fixture EOF/recovery 2 passed, no page errors. Full-batch verification remains pending.
- [x] Initial GREEN implementation present; independent spec/quality review pending. Additional integration file backend/api/routes/query.py buffers done until conversation/audit persistence before delivery, so immediate reader closure cannot lose the successful exchange.
- [x] Task 1 reviews: spec and quality approved after callback-abort, accurate queue timing, unknown duration and conversation-creation race regressions. Latest focused frontend 16 passed; focused Python including subagent contract 16 passed. Full backend checkpoint 259 passed. Existing failed-subagent progress/audit success labeling is a reviewer-noted inherited Minor limitation, not a new timing measurement.

## Task 2: Audit retrieval

Files: backend/api/v1/conversations/conversations.py; backend/services/conversation_service.py; frontend/src/api/modules/conversations.ts; frontend/src/composables/useAuditList.ts; frontend/src/views/AgentAuditView.vue; related regression tests.

- [x] RED: title/session search uses same predicates for count and page; literal wildcard escaping; deterministic pages; search/page reset; races/disposal preserve current results; deep-linked session can load outside first page. Initial unsupported service search/API count/composable paging failures observed.
- [x] GREEN: additive validated query parameters and UI search/pager/session selection; retain first-batch independent detail/trace errors.
- [x] Focused pytest 2 and Vitest 5 passed independently in both reviews; spec and quality approved. Implementer full frontend 101 and type-check passed. Root actual rendered browser search/clear/ID deep-link/outside-page selection passed with current backend GET routing, no page errors.

## Task 3: Event operations

Files: frontend/src/views/EventCenterView.vue; frontend/src/api/modules/events.ts; backend/api/routes/events.py and backend/services/event_service.py only where existing pagination/validation is insufficient; focused composable/component and route tests.

- [x] RED: filtered paging, stale requests, failed list distinct from empty, rejected status write leaves original state, selecting another event during save cannot mutate it, relation 404 distinct from 500, drawer close/unmount invalidate responses. Stable timestamp tie regression failed before id DESC addition; quality review found A→B→A save race, reproduced and added RED regression.
- [x] GREEN: use existing paginated API; update displayed status only on confirmed success, serialize per-event save, refresh current filtered list; independent relation error/retry. Reopened same event now receives successful confirmation; different selection remains isolated.
- [x] Spec and quality approved after correction; latest focused frontend 9 passed, backend 9 passed independently, type-check passed. Root full frontend checkpoint 109 passed before extra race test; browser event page2, rejected save and relation 500/404 passed without real writes.

## Task 4: Configuration effectiveness

Files: frontend/src/components/agents/config/{ParamsPanel,StrategyPanel,ProvidersPanel,McpPanel,ServiceControl}.vue; backend/api/v1/agents/config/routes.py and backend/services/{agent_params,agent_strategy}.py if contract needs correction; focused tests.

Backend milestone reviewed separately before frontend implementation: timeout consumer wired; sync/SSE context guard unified; next-read metadata; actual persisted keys/effects; reachable versus initialized readiness; hidden restart launch. Spec caught integral-float string persistence, quality caught non-finite overflow validation; both fixed with RED/GREEN tests and clean re-review. Root latest test_config_effectiveness.py: 20 passed. Backend milestone changes also include agent_service_control.py, scripts/start_agent.py and action_classifier.py. Frontend milestone remains pending.

- [x] RED: persisted is not runtime-effective; registry restart versus next-turn classifications match consumers; failed save/restart does not claim activation; unsaved edits remain protected. Deferred-provider and MCP tests detect draft loss and stale test certification. Service regressions cover old-ready color after failed read, stale refresh and duplicate confirmations.
- [x] GREEN: surface authoritative save response and effect classifications; explicit restart remains user-confirmed with confirmation latch. Saved/applied field baselines retain concurrent edits and secrets; central dirty guards and read timing labels in place. No actual configuration mutations or restarts during tests.
- [x] Backend and frontend milestones each passed spec then quality review after corrections. Root full backend 283 passed (14 inherited warnings); frontend implementer checkpoint 119 passed/type-check/build before latest service regressions. Latest independent focused config 11 passed. Root actual browser 9 flows passed, including config timing, dirty cancellation, unready restart and failed-ready color.

## Task 5: Graph/log navigation

Files: frontend/src/views/{KnowledgeGraphView,LogsView,TraceView}.vue; existing graph store/API and focused tests as necessary.

- [x] RED: route focus change honored, invalid target distinct from transport error, filtered/absent graph target handled, delayed old selection ignored; logs failure not empty, page/filter races guarded, session trace links valid. Actual Pinia/SFC regressions reproduced before implementation; separate API URL encoding RED/GREEN.
- [x] GREEN: reuse existing graph focus and log trace routes, independent error/retry, generation and disposal guards. Focus uses fetched node type metadata, not ID prefix. No new tracing adapter.
- [x] Spec and quality approved after sidebar-presence resize correction (pending/404/500 detail also changes canvas width). Latest focused 12 passed/type-check passed; root browser 11 flows passed including actual pattern/service reactive focus, hidden reveal, 404/500 retry and session log links. Root full frontend checkpoint 132 passed/build/type-check before last resize test; final rerun pending.

## Final acceptance

- [x] Latest full frontend: 22 files / 133 tests passed; fresh type-check and build exit 0 after final resize fix. Full backend/tests and tests: 283 passed, 14 inherited warnings. git diff --check exit 0 (line-ending warnings only).
- [x] Browser: 11 Batch 2 flows pass in both current-code in-process and running-services modes; no page errors. First-batch 6 browser flows also pass in both modes. Event/configuration mutations are intercepted fixtures, never real status or provider writes. Screenshots: logs/batch2-verification (ignored).
- [x] Original-checkout backend and Agent restarted hidden after validating old port/PID ownership. Frontend :5173 PID 5784; backend :8000 PID 10004; Agent :8642 PID 20152; InfluxDB :8086 PID 16272. Agent health initialized=true; config service status ready=true. Simulator left running unchanged.
- [x] Final independent integration review ready with no blocking issues; latest focused reviewer checks: navigation 12 frontend tests, stream lifecycle/proxy 11 Python, configuration effectiveness 20 Python. Keep development branch and mixed edits, no commit/push/merge/worktree.

### Live and business acceptance

- `python scripts/verify_batch2_agent.py`: genuine no-tool model query, 18,375 ms end-to-end, queue 0 ms, Agent turn approximately 6,531 ms. Total includes classification, transport and persistence; do not interpret this one simple query as a throughput or four-subagent speedup benchmark.
- Successful SSE reader closed immediately on done; conversation `f805541f-5304-49b6-bdb5-8232599136b0` already contains 2 messages and master decision. The clearly labelled acceptance conversation is retained for inspection. No business knowledge or event mutation requested.
- `python scripts/verify_batch1_business.py --http`: all 15,568 original sampling timestamps, numeric values and source hashes match; both-plant COD and multi-plant evidence verified; running HTTP checked.
- Existing warnings remain: polling test lifecycle warnings, dependency deprecations, Rollup annotations, mixed dynamic/static import and roughly 1.99 MB main bundle. Prometheus business-gauge skip warnings remain outside this batch.
- Inherited Minor limitation: failed subagent progress can still use stage=done and audit status=success; this is not fixed or claimed correct by the elapsed-time changes. Complete per-turn tracing, parallel throughput, authentication and expert knowledge approval remain deferred.
