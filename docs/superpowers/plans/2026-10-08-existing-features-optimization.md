# Existing Features Optimization Implementation Plan

> **For agentic workers:** Execute inline using executing-plans, test-driven-development and verification-before-completion. Work in the original checkout on `codex/hermes-phase1-hardening`; do not create a worktree, merge the paper branch, or modify unrelated local settings.

**Goal:** Improve existing functionality in three independently verified batches without implementing deferred subsystems.

**Architecture:** Keep InfluxDB as the wastewater business store. File import and future API adapters must share canonical sampling timestamps, provenance and plant-scoped queries. Keep real and simulated data separate without guessing the origin of existing mixed records. Separate service availability from business data recency. UI request failure must not be presented as absence of data.

**Tech Stack:** FastAPI, pandas, InfluxDB, Vue 3, TypeScript, Vitest, pytest.

## Batch boundaries and checkpoints

- [x] Batch 1: provenance/time, dashboard/metrics consistency, AI evidence, audit reliability. Acceptance recorded below.
- [x] Batch 2: measured AI latency and failure UX, audit retrieval, events, configuration effectiveness, graph/log navigation. Acceptance recorded below and in the detailed Batch 2 plan.
- [x] Batch 3: layout, scrolling, wording, empty states, navigation and unavailable entry points. Accepted 2026-10-15; detailed evidence in `2026-10-15-batch3-experience-convergence.md`.

Do not count a batch as complete when only one increment passes tests. Record each verified increment below. New authentication/approval workflows, job queues, tracing adapters, event sources, report exporters and regulator API adapters are excluded. Prometheus/Grafana are excluded.

## Batch 1, increment 1: reliable audit detail retrieval

**Files:** Create `frontend/src/composables/useAuditDetail.ts`; test `frontend/src/composables/__tests__/useAuditDetail.spec.ts`; modify `frontend/src/views/AgentAuditView.vue`.

- [x] Write regression cases: delayed A cannot replace selected B; stale failure cannot replace B; independent trace failure preserves conversation; empty successful trace is distinct from failed request; retry clears prior errors; dispose invalidates pending writes.
- [x] Run `E:\nodejs\npm.cmd test -- src/composables/__tests__/useAuditDetail.spec.ts` in frontend and record the expected red result.
- [x] Extract detail retrieval into a composable with injectable `detail(id)` and `trace(id)` dependencies. Use a monotonically increasing request generation; before any state mutation after asynchronous work, require the active generation. Start detail and trace together but settle independently. Track `detailError`, `traceError`, `loadingDetail`, `loadingTrace` separately. Empty trace means every evidence collection is empty and both master decision and API call are absent. Treat rejected requests as errors, not emptiness.
- [x] Integrate state into the existing view. Expose separate loading, retry and empty states. Explicitly label the trace as latest recorded turn: the existing backend returns latest decision/subagent turn, not an all-turn trace. Invalidate requests on unmount.
- [x] Re-run targeted tests, all frontend tests, `npm run type-check`, `npm run build`; inspect diff for unrelated edits and error/empty conflation.

## Remaining Batch 1 work: investigate before migration

- [x] Map import and simulator writer, shared queries, plant dashboard queries, data-service routes, agent canonical scripts and timestamp conventions. Inspect original report availability and current bucket contents with read-only queries.
- [x] Define and test provenance for real file/API records and simulated records; never classify old data solely by timestamp. Preserve old bucket. Require a dry-run count and original-file traceability before rebuilding a real dataset.
- [x] Test explicit plant/source scoping, cache invalidation, missing-side records, timezone boundaries, and identical dashboard/metrics aggregation. No silent zero substitution for missing measurements.
- [x] Verify fixed business cases through AI evidence and audit with the same plant/source/time interval; report any unavailable model endpoint separately from code correctness.

Each subsequent increment receives concrete file-level tests and changes after this mapping. The three-batch list is a scope roadmap, not a claim that unspecified changes have been implemented.

## Verified progress, 2026-10-08

The following is the earlier increment-1 checkpoint. Full Batch 1 acceptance is recorded in the final section below.

- [x] Regression tests reproduced six old detail/trace failure and race cases. A later regression reproduced selection after disposal, and another reproduced HTTP-200 `success:false` detail envelopes.
- [x] Implemented independent loads, request generations, disposal guard, distinct empty/error states and retry.
- [x] Integrated into AgentAuditView with explicit latest-decision/session-level trace scope labels.
- [x] Read-only reviewer findings were verified against backend contracts and fixed.
- [x] Final verification: 60 frontend tests pass (12 audit cases); type-check passes; production build passes; `git diff --check` passes; dev route `/agents/audit` returns HTTP 200. Browser interaction and visual QA have not been performed.

Existing warnings remain: two usePolling lifecycle warnings in tests, Rollup dependency annotation warnings, mixed static/dynamic API imports, and a roughly 1.99 MB main bundle. No changes were made to business data, credentials, paper branches, Prometheus or Grafana in this increment.

Read-only mapping identified the next items: unscoped relative metric queries, hardcoded custom-range plant and seven-day truncation, permanently cached loader, report timestamps treated as UTC, and an accelerated simulator sharing the business bucket. These were addressed in the following increment.

## Batch 1 final acceptance, 2026-10-08

- [x] Source contract: separate `monitoring-real` and `monitoring-simulation`; retain legacy `monitoring-data` as unverified. Declared source queries also require matching `data_origin`, not merely the bucket name. Report timestamps use `DATA_TIMEZONE=Asia/Shanghai`, UTC storage and local query semantics. Source filename, SHA-256, ingestion method and timezone are preserved as fields.
- [x] Import dry-run and actual migration: 3 original XLS reports, 15,568 sampling records. The read-only acceptance script checks every imported sampling timestamp, numeric value and file hash against the original report. No legacy bucket deletion or rewrite.
- [x] Shared query contract: explicit plant selection, escaped Flux literals, empty-table handling, source filters, independently missing sides and dynamic numeric indicators. Plant discovery drops mixed-type `_value` columns before regrouping; actual database and browser checks caught and verified this regression.
- [x] Dashboard and metrics: same endpoint and selected plant; latest-sample-relative elapsed windows; custom inclusive end dates without seven-day truncation; anchor-only replay remains seven days; all-history 10000-hour button remains supported. Shared union timeline, latest finite values, finite statistics, stale-request/unmount protection, local tree timestamps and visible source/freshness metadata.
- [x] Legacy monitoring API: plant-scoped 15-second cache refresh; no arbitrary-plant CSV fallback; missing flow is null; effluent-only raw/aggregated queries work; missing/all-null sum buckets are null. Daily system history and discovery use the same source/timezone rules.
- [x] AI evidence: data perception and anomaly fallback share plant/time bounds, CLI hours are honored; compact result carries source and sampling/query ranges. Sync and SSE append server-generated session evidence; a failed last plant cannot suppress earlier successful plant evidence. Historical/simulated/unknown source, carried snapshot and assisted-review caveats are explicit.
- [x] Audit: conversation and trace settle independently with selection generations and disposal guards. Separate empty/failure/retry states for detail, trace and list. Scope clearly distinguishes latest-turn decisions/subagents from session-level operator/model records.
- [x] Spec and quality reviews: confirmed findings fixed with regression tests; subsequent independent review found no remaining Important issues in the reviewed scope.
- [x] Latest complete regression: `python -m pytest backend/tests tests -q --tb=short` => 249 passed; frontend `npm test` => 83 passed; type-check and production build exit 0. `git diff --check` passes. Existing dependency/config warnings and approximately 1.99 MB main bundle remain.
- [x] Real business acceptance: `python scripts/verify_batch1_business.py --http` passes against the running backend and configured InfluxDB. Both plants' July 14–15 COD series match the canonical data-perception results; multi-plant server evidence is verified using temporary artifacts only.
- [x] Browser acceptance: `python scripts/verify_batch1_ui.py` passes 6 flows with no page errors: dates/source metadata, effluent-only missing state, injected metric failure and recovery, all-history dashboard, latest-turn audit scope, and injected audit-list failure and recovery. Screenshots are under `logs/batch1-verification/` (ignored runtime output). Also verified current-code in-process mode. Native browser automation failed initialization, so local Playwright was used.
- [x] Actual Agent smoke: synchronous query returned HTTP 200 in 46.6 seconds, correct COD statistics and server source/footer; SSE follow-up returned done in 3.9 seconds with the carried snapshot's evidence/history/manual-review footer. Conversation ID: `e4874e20-7dfd-4f73-b976-5dff19b05392` (an acceptance-test conversation retained for audit).
- [x] Persisted audit acceptance: conversation detail and trace endpoints both return HTTP 200; four messages (sync + SSE exchanges) are recorded, both assistant messages retain the server evidence footer, and the latest master decision is present. Agent smoke also updates the existing runtime `skills/.usage.json`; this is not a source-code change.
- [x] Runtime: backend :8000 and Agent :8642 restarted from the original checkout; frontend :5173 and InfluxDB :8086 remain up. Old simulator stopped; corrected simulator writes only `monitoring-simulation`. Real business COD count remains 15,443; legacy bucket still exists with 21,083 COD records. Simulated future timestamps are not real freshness evidence.

### Verified source inventory

| Plant | Side | Sampling records | Latest local sampling time |
| --- | --- | ---: | --- |
| 当阳市金桥污水处理厂一期 | effluent | 4,935 | 2026-07-25 14:00 |
| 当阳市金桥污水处理厂一期 | influent | 4,935 | 2026-07-25 14:00 |
| 洗舱站污水排放口 | effluent | 5,698 | 2026-08-26 09:00 |

### Operating and compatibility notes

- `.env` now selects `INFLUXDB_BUCKET=monitoring-real`, declares both isolated buckets, `BUSINESS_DATA_MODE=historical` and `DATA_TIMEZONE=Asia/Shanghai`. `.env.example` documents these non-secret settings. Credentials were not changed.
- Future regulator API ingestion must write the same real-source contract (`data_origin=real`, original sample timestamp, source/ingestion metadata). When a sustained feed is available, switch `BUSINESS_DATA_MODE` to `live`; it then evaluates stale/future sampling. The adapter itself is deferred, not implemented here.
- To inspect/temporarily restore legacy data, select `monitoring-data` and restart consumers; it is intentionally unverified, never automatically promoted to real. Do not point the simulator at either business/real bucket. No destructive rollback is needed.
- Existing monitoring routes now require `plant_id`; third-party callers must supply it. CSV has no validated plant mapping and therefore refuses plant-scoped requests instead of silently mixing data.
- Prometheus/Grafana were not changed. Their old unscoped business-gauge updater now skips updates with a warning under the mandatory plant guard; future system-monitoring integration remains deferred.
- One early anomaly CLI test accidentally wrote an ignored `subagents/anomaly-detection-agent/anomaly_result.json` failed test artifact. Later tests use temporary sessions. Its prior content could not be established, so it was retained, not deleted; it is not a real analysis result.
- Authentication, authorization, expert knowledge diff/confirmation/audit/rollback, latency/concurrency optimization and Batch 2/3 work are not claimed complete. Keep the existing development branch in the original checkout; no paper merge, worktree, push or merge to main was performed.

## Batch 2 final acceptance, 2026-10-08

This supersedes the earlier Batch 1 checkpoint's pending Batch 2 status. Batch 3 remains pending.

- [x] AI stream lifecycle: exact terminal settlement, interrupted partial answer retained with failure, session/creation races guarded; measured total/queue/Agent-turn/subagent durations. Successful conversation/audit persistence occurs before delivery of done.
- [x] Audit retrieval: validated literal title/session search, deterministic count/pagination, search/clear/pager UI, external session links and preserved outside-page detail.
- [x] Events: stable filtered pages; confirmed per-event status writes, current-filter refresh, reopened same-event synchronization; independent relation error/retry and 404 empty state.
- [x] Configuration: actual timeout/context consumers corrected; read-time metadata; saved-versus-runtime wording, applied-field baselines, concurrent draft protection, dirty navigation guards, MCP test validity, readiness-aware confirmed and deduplicated restart.
- [x] Graph/logs: actual-type reactive focus, hidden-node reveal, selection/disposal/resize guards; session-ID trace links; trace route changes, failures/retry and successful empty records distinguished.
- [x] Each milestone passed spec and quality review with regressions for confirmed findings; final integration review found no blocking issues.
- [x] Complete regressions: backend 283 passed; frontend 133 passed; type-check, production build and diff check passed. Existing warnings and bundle size remain.
- [x] Running-services browser acceptance: 11 Batch 2 flows and 6 Batch 1 flows passed, no page errors. Actual model smoke confirms messages and audit persisted before immediate SSE closure. Original data business acceptance still matches all 15,568 records.
- [x] New code loaded by original-checkout backend :8000 and Agent :8642; initialized/ready true. Frontend :5173, InfluxDB :8086 and simulator retained. Branch codex/hermes-phase1-hardening preserved, mixed edits remain uncommitted.

Detailed tests, timing, service PIDs, acceptance conversation and remaining Minor audit-status caveat are recorded in `docs/superpowers/plans/2026-10-08-batch2-optimization.md`. Parallel Agent execution, full per-round audit and authentication/expert knowledge approvals are not claimed implemented.
