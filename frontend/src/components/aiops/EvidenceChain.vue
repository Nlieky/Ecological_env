<template>
  <div class="card">
    <div class="lbl">证据链 <router-link class="more" :to="`/logs/trace/${trace.session_id}`">查看完整追溯 ▸</router-link></div>

    <!-- 主决策元数据 -->
    <div class="meta" v-if="md">
      <div class="m"><div class="mh">意图</div><div class="mv">{{ md.intent || '—' }}</div></div>
      <div class="m"><div class="mh">耗时</div><div class="mv">{{ md.total_latency_ms != null ? Math.round(md.total_latency_ms) + 'ms' : '—' }}</div></div>
      <div class="m grow"><div class="mh">推理摘要</div><div class="mv sm">{{ md.reasoning_summary || '—' }}</div></div>
    </div>

    <!-- 证据链：各子智能体的关键证据（数据→异常→规则→处置） -->
    <div class="chain" v-if="chain.length">
      <div v-for="(n, i) in chain" :key="i" class="node" :class="n.status">
        <div class="nd-head">
          <span class="num">{{ i + 1 }}</span>
          <span class="nm">{{ n.cnName }}</span>
          <span class="st" :title="n.status">{{ n.status === 'success' ? '✓' : '✗' }}</span>
        </div>
        <div class="nd-body">
          <div class="evi">{{ n.summary || '(无摘要)' }}</div>
          <!-- 结构化证据 -->
          <div class="evd" v-if="n.evidence && n.evidence.kind">
            <template v-if="n.evidence.kind === 'anomaly'">
              <div class="evr">⚠ 检出 <b>{{ n.evidence.count }}</b> 个异常</div>
              <div class="evt" v-for="(a, idx) in n.evidence.top" :key="idx">
                {{ a.metric }} · {{ a.time }} · {{ a.type }} · {{ a.value }}<span v-if="a.score != null">（得分 {{ a.score }}）</span>
              </div>
            </template>
            <template v-else-if="n.evidence.kind === 'rule'">
              <div class="evr">违规判定：<b>{{ n.evidence.has_violation }}</b> · 嫌疑等级 {{ n.evidence.suspicion || '—' }}</div>
              <div class="evt" v-if="n.evidence.types && n.evidence.types.length">违规类型：{{ n.evidence.types.join('、') }}</div>
            </template>
            <template v-else-if="n.evidence.kind === 'disposition'">
              <div class="evr">预警级别：<b>{{ n.evidence.level || '—' }}</b></div>
              <div class="evt" v-if="n.evidence.disposition">{{ n.evidence.disposition }}</div>
            </template>
            <template v-else-if="n.evidence.kind === 'data'">
              <div class="evr">进水 <b>{{ n.evidence.rows_in }}</b> 条 · 出水 <b>{{ n.evidence.rows_out }}</b> 条</div>
            </template>
          </div>
          <div class="sks" v-if="n.skills.length">
            <span class="sk" v-for="s in n.skills" :key="s">📖 {{ s }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty">该会话无子智能体执行证据（未走完整 pipeline 或为早期无追踪会话）</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SessionTrace } from '@/api/types/api.types'
const props = defineProps<{ trace: SessionTrace }>()
const md = computed(() => props.trace.master_decision)

const KEY_CN: Record<string, string> = {
  'multi-dimensional-data-perception': '数据感知',
  'anomaly-detection': '异常检测',
  'rule-reasoning': '规则推理',
  'disposition-execution': '研判处置',
}

function parseOut(o: any): { summary: string; skills: string[]; evidence: any } {
  let d = o
  if (typeof o === 'string') { try { d = JSON.parse(o) } catch { d = {} } }
  if (!d || typeof d !== 'object') d = {}
  const sumRaw = (d as any).summary
  let summary = ''
  if (typeof sumRaw === 'string') summary = sumRaw
  else if (sumRaw && typeof sumRaw === 'object') summary = (sumRaw as any).summary || ''
  const sc = (d as any).skill_calls || []
  const skills = (Array.isArray(sc) ? sc : [])
    .map((s: any) => (typeof s === 'string' ? s : s?.skill || s?.name || ''))
    .filter(Boolean)
  const evidence = (d as any).evidence || {}
  return { summary, skills, evidence }
}

const chain = computed(() => {
  const exs = props.trace.subagent_executions || []
  return exs.map((e: any) => {
    const { summary, skills, evidence } = parseOut(e.output_result)
    return {
      cnName: KEY_CN[e.subagent_name] || e.subagent_name,
      summary, skills, evidence,
      status: e.status || 'success',
    }
  })
})
</script>

<style scoped>
.card { background: #fafbff; border: 1px solid #e6e9ff; border-radius: 9px; padding: 10px 12px }
.lbl { font-size: 11px; color: var(--primary); font-weight: 600; margin-bottom: 8px; display: flex; justify-content: space-between }
.more { color: var(--primary); text-decoration: none; font-weight: 400 }

.meta { display: flex; gap: 16px; padding: 6px 2px 8px; border-bottom: 1px dashed var(--brd); margin-bottom: 8px }
.m { display: flex; flex-direction: column; gap: 1px }
.m.grow { flex: 1; min-width: 0 }
.mh { font-size: 9px; color: var(--text-muted); letter-spacing: .5px }
.mv { font-size: 11px; font-weight: 600; color: var(--text-primary) }
.mv.sm { font-weight: 400; font-size: 10.5px; color: var(--text-secondary) }

.chain { display: flex; flex-direction: column; gap: 6px }
.node { background: #fff; border: 1px solid var(--brd); border-radius: 7px; padding: 6px 9px }
.node.failed { border-color: #fecaca; background: #fef2f2 }
.nd-head { display: flex; align-items: center; gap: 6px; margin-bottom: 3px }
.num { width: 15px; height: 15px; border-radius: 50%; background: var(--primary); color: #fff; font-size: 9px; font-weight: 700; display: grid; place-items: center }
.nm { font-size: 11.5px; font-weight: 700; color: var(--text-primary) }
.st { margin-left: auto; font-size: 12px; font-weight: 700 }
.node.success .st { color: #16a34a }
.node.failed .st { color: #dc2626 }
.nd-body { padding-left: 21px }
.evi { font-size: 11px; color: var(--text-secondary); line-height: 1.5 }

.evd { margin-top: 5px; padding: 5px 7px; background: rgba(99, 102, 241, 0.05); border-left: 2px solid rgba(99, 102, 241, 0.3); border-radius: 0 4px 4px 0 }
.evr { font-size: 10.5px; color: var(--text-primary); font-weight: 500 }
.evt { font-size: 9.5px; color: var(--text-muted); margin-top: 2px; line-height: 1.4 }

.sks { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px }
.sk { font-size: 9.5px; color: var(--primary); background: #eef2ff; border-radius: 4px; padding: 1px 5px }
.empty { font-size: 11px; color: var(--text-muted); padding: 6px 2px }
</style>
