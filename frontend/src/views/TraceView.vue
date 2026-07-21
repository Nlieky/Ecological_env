<template>
  <div class="trc" v-if="loaded">
    <div v-if="trace">
      <div class="head">
        <span class="ttl">会话追溯</span>
        <span class="sid">{{ trace.session_id }}</span>
      </div>

      <!-- 主智能体决策摘要 -->
      <section class="card" v-if="md">
        <div class="sec-ttl">主智能体决策</div>
        <div class="grid">
          <div><span class="k">意图</span><span class="v">{{ md.intent || '—' }}</span></div>
          <div><span class="k">耗时</span><span class="v">{{ md.total_latency_ms != null ? Math.round(md.total_latency_ms) + ' ms' : '—' }}</span></div>
          <div><span class="k">用户查询</span><span class="v wrap">{{ md.user_query || '—' }}</span></div>
          <div><span class="k">决策路径</span><span class="v wrap">{{ (md.decision_path || []).join(' → ') || '—' }}</span></div>
          <div><span class="k">子智能体</span><span class="v wrap">{{ (md.subagents_called || []).join('、') || '无' }}</span></div>
          <div><span class="k">推理摘要</span><span class="v wrap">{{ md.reasoning_summary || '—' }}</span></div>
        </div>
      </section>

      <!-- 推理卡片（复用 Phase 2） -->
      <div class="cards">
        <DecisionFlow :trace="trace" />
        <SubAgentChips :trace="trace" />
        <EvidenceChain :trace="trace" />
      </div>

      <!-- 子智能体执行明细 -->
      <section class="card">
        <div class="sec-ttl">子智能体执行 <span class="cnt">{{ (trace.subagent_executions || []).length }}</span></div>
        <div v-if="(trace.subagent_executions || []).length" class="calls">
          <div v-for="(c, i) in trace.subagent_executions" :key="i" class="call">
            <span class="c-name">{{ c.subagent_name || c.name || `子智能体 ${i + 1}` }}</span>
            <span class="c-meta" v-if="c.latency_ms != null">{{ Math.round(c.latency_ms) }} ms</span>
            <span class="c-meta">{{ c.status || c.result || '—' }}</span>
          </div>
        </div>
        <div v-else class="empty">暂无子智能体执行记录（agent 服务未回传）</div>
      </section>

      <!-- 算子调用 -->
      <section class="card">
        <div class="sec-ttl">算子调用 <span class="cnt">{{ (trace.operator_calls || []).length }}</span></div>
        <el-table v-if="(trace.operator_calls || []).length" :data="trace.operator_calls" size="small" border>
          <el-table-column v-for="k in opCols" :key="k" :prop="k" :label="k" min-width="120" show-overflow-tooltip />
        </el-table>
        <div v-else class="empty">暂无算子调用记录</div>
      </section>

      <!-- LLM 调用 -->
      <section class="card">
        <div class="sec-ttl">LLM 调用 <span class="cnt">{{ (trace.llm_calls || []).length }}</span></div>
        <el-table v-if="(trace.llm_calls || []).length" :data="trace.llm_calls" size="small" border>
          <el-table-column v-for="k in llmCols" :key="k" :prop="k" :label="k" min-width="120" show-overflow-tooltip />
        </el-table>
        <div v-else class="empty">暂无 LLM 调用记录</div>
      </section>
    </div>

    <div v-else class="state err">⚠ 未找到该会话的追溯数据（session_id：{{ id }}）。</div>
  </div>
  <div v-else class="state">加载追溯中…</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { logsService } from '@/api/modules/logs'
import DecisionFlow from '@/components/aiops/DecisionFlow.vue'
import SubAgentChips from '@/components/aiops/SubAgentChips.vue'
import EvidenceChain from '@/components/aiops/EvidenceChain.vue'
import type { SessionTrace } from '@/api/types/api.types'

const route = useRoute()
const id = computed(() => String(route.params.id))
const trace = ref<SessionTrace | null>(null)
const loaded = ref(false)
const md = computed(() => trace.value?.master_decision || null)

// 动态列：取首条记录的键
const opCols = computed(() => keysOf(trace.value?.operator_calls))
const llmCols = computed(() => keysOf(trace.value?.llm_calls))
function keysOf(arr?: Record<string, unknown>[]) {
  if (!arr || !arr.length) return [] as string[]
  return Object.keys(arr[0])
}

onMounted(async () => {
  try { trace.value = await logsService.trace(id.value) }
  catch { trace.value = null }
  finally { loaded.value = true }
})
</script>

<style scoped>
.trc { display: flex; flex-direction: column; gap: 14px; max-width: 1000px }
.head { display: flex; align-items: baseline; gap: 14px; margin-bottom: 2px }
.ttl { font-size: 17px; font-weight: 700 }
.sid { font-size: 12px; color: var(--text-muted); font-family: ui-monospace, monospace }
.card { background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px; padding: 15px 17px;
  box-shadow: var(--card-shadow) }
.sec-ttl { font-size: 13px; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px }
.sec-ttl::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.cnt { font-size: 11px; color: var(--text-muted); font-weight: 400 }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 24px }
.grid > div { display: flex; flex-direction: column; gap: 2px; min-width: 0 }
.k { font-size: 11px; color: var(--text-muted) }
.v { font-size: 13px; color: var(--text-primary); font-weight: 500 }
.v.wrap { word-break: break-all; font-weight: 400; font-size: 12.5px }
.cards { display: flex; flex-direction: column; gap: 10px }
.calls { display: flex; flex-direction: column; gap: 8px }
.call { display: flex; align-items: center; gap: 12px; padding: 9px 12px; background: var(--surface-1);
  border: 1px solid var(--brd); border-radius: 9px }
.c-name { font-size: 13px; font-weight: 600; color: var(--text-primary); flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.c-meta { font-size: 11.5px; color: var(--text-secondary) }
.empty { color: var(--text-muted); font-size: 12px; padding: 6px 0 }
.state { color: var(--text-muted); font-size: 14px; padding: 40px 0; text-align: center }
.state.err { color: var(--danger) }
</style>
