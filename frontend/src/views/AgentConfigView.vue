<template>
  <div class="cfg" v-if="caps">
    <!-- 主智能体 -->
    <section class="card master">
      <div class="master-head">
        <div class="avatar">🧠</div>
        <div>
          <div class="mname">{{ caps.master_agent.name }}</div>
          <div class="mrole">{{ caps.master_agent.role }}</div>
        </div>
        <span class="loc">{{ caps.master_agent.location }}</span>
      </div>
      <div class="impl">
        <span class="impl-k">实现</span>
        <span class="impl-v">{{ caps.implementation.method }}</span>
        <span class="impl-d">{{ caps.implementation.description }}</span>
      </div>
      <div class="files">
        <span class="files-k">加载的身份文件</span>
        <div class="chips">
          <span v-for="f in caps.implementation.identity_files_loaded" :key="f" class="chip">{{ shortFile(f) }}</span>
        </div>
      </div>
    </section>

    <!-- 决策树 -->
    <section class="card">
      <div class="sec-ttl">决策树 · 意图识别与子智能体调度</div>
      <div class="tree">
        <div v-for="node in caps.decision_tree" :key="node.step" class="tstep">
          <div class="tnum">{{ node.step }}</div>
          <div class="tbody">
            <div class="tq">{{ node.question }}</div>
            <div v-if="node.condition" class="tcond">触发条件：{{ node.condition }}</div>
            <div class="tacts">
              <span v-if="node.yes_action" class="act yes">✓ {{ node.yes_action }}</span>
              <span v-if="node.no_action" class="act no">✗ {{ node.no_action }}</span>
              <span v-if="node.action" class="act done">→ {{ node.action }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 子智能体 -->
    <section class="card">
      <div class="sec-ttl">子智能体 · 4 个专职执行体</div>
      <div class="subs">
        <div v-for="s in caps.sub_agents" :key="s.name" class="sub">
          <div class="sicon">{{ subVibe(s.name).icon }}</div>
          <div class="sname">{{ subVibe(s.name).label }}</div>
          <div class="srole">{{ s.role }}</div>
          <div class="sloc">{{ s.location }}</div>
        </div>
      </div>
    </section>
  </div>

  <div v-else-if="loading" class="state">加载智能体配置中…</div>
  <div v-else class="state err">⚠ 加载失败，请确认后端服务可用后刷新。</div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { queryService } from '@/api/modules/query'
import type { CapabilitiesResponse } from '@/api/types/api.types'

const caps = ref<CapabilitiesResponse | null>(null)
const loading = ref(true)

// 子智能体名 → 中文标签 + vibe 图标（来自系统架构定义）
const VIBES: Record<string, { icon: string; label: string }> = {
  'multi-dimensional-data-perception': { icon: '📊', label: '多维数据感知' },
  'anomaly-detection': { icon: '🔍', label: '异常检测' },
  'rule-reasoning': { icon: '⚖️', label: '规则推理' },
  'disposition-execution': { icon: '🚨', label: '研判预警与处置' },
}
function subVibe(name: string) {
  for (const k of Object.keys(VIBES)) if (name.includes(k)) return VIBES[k]
  return { icon: '🤖', label: name }
}
function shortFile(f: string) { return f.replace(/^workspace\//, '').replace(/^subagents\//, '') }

onMounted(async () => {
  try { caps.value = await queryService.capabilities() }
  catch { caps.value = null }
  finally { loading.value = false }
})
</script>

<style scoped>
.cfg { display: flex; flex-direction: column; gap: 16px; max-width: 980px }
.card { background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px; padding: 16px 18px;
  box-shadow: var(--card-shadow) }
.sec-ttl { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 14px;
  display: flex; align-items: center; gap: 8px }
.sec-ttl::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }

/* 主智能体 */
.master-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px }
.avatar { width: 46px; height: 46px; border-radius: 12px; background: var(--brand-gradient); display: grid; place-items: center; font-size: 22px }
.mname { font-size: 17px; font-weight: 700; color: var(--text-primary) }
.mrole { font-size: 12.5px; color: var(--text-secondary); margin-top: 2px }
.loc { margin-left: auto; font-size: 11px; color: var(--text-muted); background: #f1f5f9; border: 1px solid var(--brd); padding: 4px 10px; border-radius: 6px; font-family: ui-monospace, monospace }
.impl { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; padding: 10px 0; border-top: 1px dashed var(--brd) }
.impl-k { font-size: 11px; color: var(--text-muted); letter-spacing: .5px }
.impl-v { font-size: 12.5px; font-weight: 600; color: var(--primary) }
.impl-d { font-size: 12px; color: var(--text-secondary); flex-basis: 100% }
.files { padding-top: 10px; border-top: 1px dashed var(--brd) }
.files-k { font-size: 11px; color: var(--text-muted); letter-spacing: .5px }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px }
.chip { font-size: 11.5px; font-family: ui-monospace, monospace; background: #f8fafc; border: 1px solid var(--brd); padding: 3px 9px; border-radius: 6px; color: var(--text-secondary) }

/* 决策树 */
.tree { display: flex; flex-direction: column; gap: 10px }
.tstep { display: flex; gap: 12px }
.tnum { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; display: grid; place-items: center;
  background: var(--primary); color: #fff; font-size: 12px; font-weight: 700 }
.tbody { flex: 1; min-width: 0 }
.tq { font-size: 13px; font-weight: 600; color: var(--text-primary) }
.tcond { font-size: 11.5px; color: var(--text-muted); margin-top: 2px }
.tacts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px }
.act { font-size: 11.5px; padding: 3px 9px; border-radius: 6px; border: 1px solid var(--brd) }
.act.yes { color: #047857; background: #ecfdf5; border-color: #a7f3d0 }
.act.no { color: #64748b; background: #f8fafc }
.act.done { color: var(--primary); background: #eef2ff; border-color: #c7d2fe; font-weight: 600 }

/* 子智能体 */
.subs { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px }
.sub { border: 1px solid var(--brd); border-radius: 11px; padding: 14px; background: #fff; transition: border-color .15s }
.sub:hover { border-color: var(--primary) }
.sicon { font-size: 24px }
.sname { font-size: 14px; font-weight: 700; color: var(--text-primary); margin-top: 6px }
.srole { font-size: 12px; color: var(--text-secondary); margin-top: 2px }
.sloc { font-size: 10.5px; color: var(--text-muted); margin-top: 8px; font-family: ui-monospace, monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis }

.state { color: var(--text-muted); font-size: 14px; padding: 40px 0; text-align: center }
.state.err { color: var(--danger) }
</style>
