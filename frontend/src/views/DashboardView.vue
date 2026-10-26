<template>
  <PageShell title="监测大屏" subtitle="按厂站查看采样趋势与数据来源" scroll="auto" class="dash-page">
    <template #toolbar>
    <!-- 顶部：三个可切换选项卡（参考 aiops.hgdz.cn：仪表盘/系统态势/态势历史） -->
    <div class="top-tabs">
      <button v-for="t in TOP_TABS" :key="t.v" :class="{ on: tab === t.v }" @click="tab = t.v">{{ t.t }}</button>
    </div>
    </template>

    <!-- 仪表盘 tab：看板列表(市→厂区→厂) + 选中厂流式看板 -->
    <div v-if="tab === 'dash'" class="dash-layout">
      <div class="dash-side">
        <div class="dash-side-ttl">看板列表</div>
        <PlantTree @select="onPickPlant" />
      </div>
      <div class="dash-main">
        <PlantBoardPanel v-if="store.activePlant" ref="boardRef" :key="store.activePlant" :plant-id="store.activePlant" />
        <div v-else class="placeholder">
          <div class="ph-ico">🏭</div>
          <div class="ph-t">从左侧看板列表选择厂站</div>
          <div class="ph-d">市 → 厂区 → 厂，点击具体厂查看该厂各指标流式曲线</div>
        </div>
      </div>
    </div>

    <!-- 系统态势 / 态势历史 tabs -->
    <SystemStatusView v-else-if="tab === 'sys'" />
    <SituationHistoryView v-else />
  </PageShell>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import PageShell from '@/components/common/PageShell.vue'
import { usePlantsStore } from '@/stores/plants'
import { useActionStore } from '@/stores/action'
import PlantTree from '@/components/cockpit/PlantTree.vue'
import PlantBoardPanel from '@/views/PlantBoardPanel.vue'
import SystemStatusView from '@/views/SystemStatusView.vue'
import SituationHistoryView from '@/views/SituationHistoryView.vue'
import { useAssistantContext } from '@/composables/useAssistantContext'
import { useAssistantContextStore } from '@/stores/assistantContext'
import { contextPolicy } from '@/assistant/contextPolicy'
import api from '@/api/client'
import type { Annotation } from '@/stores/action'

// 顶部三个选项卡（同参考站：仪表盘 / 系统态势 / 态势历史）
const TOP_TABS = [
  { t: '仪表盘', v: 'dash' }, { t: '系统态势', v: 'sys' }, { t: '态势历史', v: 'hist' },
] as const
const tab = ref<'dash' | 'sys' | 'hist'>('dash')
const boardRef = ref<InstanceType<typeof PlantBoardPanel>>()

const store = usePlantsStore()
const route = useRoute()

function onPickPlant(pid: string) {
  store.selectPlant(pid)  // 记选中（父级链展开由 PlantTree 内部处理）
}

// 首次进入：自动选中第一棵树第一个厂（树加载完后）
let disposed = false
onBeforeUnmount(() => { disposed = true })
function selectRoutePlant() {
  const plant = route.query.plant
  if (disposed || typeof plant !== 'string' || !plant.trim()) return false
  store.selectPlant(plant)
  if (store.tree) store.expandTo(plant)
  tab.value = 'dash'
  return true
}
watch(() => route.query.plant, selectRoutePlant)
watch(() => store.tree, () => { if (store.tree) selectRoutePlant() })
store.fetchTree().then((t) => {
  if (!disposed && t && !selectRoutePlant() && !store.activePlant) {
    const first = t.cities?.[0]?.districts?.[0]?.plants?.[0]
      || t.ungrouped?.[0]
    if (first) {
      store.selectPlant(first.plant_id)
      store.expandTo(first.plant_id)
    }
  }
})

// AI 动作指令带厂名时:大屏自动切到该厂(如"检测金桥厂COD异常")
const actionStore = useActionStore()
const assistantContext = useAssistantContextStore()
watch(() => actionStore.plant, (p) => {
  if (!p) return
  // 树里模糊匹配厂名(允许简称,如"金桥"匹配"当阳市金桥污水处理厂一期")
  const cands: string[] = []
  for (const c of store.tree?.cities ?? []) {
    for (const d of c.districts ?? []) for (const pl of d.plants ?? []) cands.push(pl.plant_id)
  }
  for (const pl of store.tree?.ungrouped ?? []) cands.push(pl.plant_id)
  const hit = cands.find((id) => id === p) || cands.find((id) => id.includes(p) || p.includes(id))
  if (hit && hit !== store.activePlant) {
    store.selectPlant(hit)
    store.expandTo(hit)
  }
})
// 动作到达时确保在仪表盘 tab(用户可能正看系统态势)
watch(() => actionStore.lastAction, () => { tab.value = 'dash' })
useAssistantContext(() => ({ pageId: 'dashboard', plant: store.activePlant || null, indicator: actionStore.indicators?.join(',') || null, range: actionStore.viewContext.segmentStart ? { start: actionStore.viewContext.segmentStart, end: actionStore.viewContext.segmentEnd || '' } : null, source: store.dashboard?.data_context?.bucket || '厂站大屏（来源未核验）', freshness: store.dashboard?.data_context?.freshness || null, filters: { tab: tab.value, side: actionStore.side }, status: store.dashboardLoading ? 'loading' : store.dashboardError ? 'error' : store.dashboard ? 'ready' : 'empty', actions: ['navigate', 'dashboard.view', 'dashboard.range', 'dashboard.detect'] }), async action => {
  if (!['dashboard.view', 'dashboard.range', 'dashboard.detect'].includes(action.capability)) return { success: false, message: '大屏不支持该操作' }
  const p = action.parameters
  if (action.capability === 'dashboard.detect') {
    const plant = store.activePlant
    const vc = { ...actionStore.viewContext }
    const source = store.dashboard?.data_context?.bucket || ''
    if (!plant || vc.plant !== plant || !vc.segmentStart || !vc.segmentEnd) return { success: false, message: '当前厂站采样窗口尚未核验，无法检测' }
    const expected = { algorithm: String(p.algorithm), indicator: String(p.indicator === 'AN' ? 'NH3-N' : p.indicator === 'suspended_solids' ? 'SS' : p.indicator), side: String(p.side), plant, start: vc.segmentStart, end: vc.segmentEnd, source }
    const response = await api.post<unknown, { success: boolean; error?: string; data?: { status?: string; execution_context?: Record<string, string>; actionData?: { annotations?: Annotation[] } } }>('/v1/detection/run', {
      algorithm: p.algorithm, indicator: p.indicator === 'AN' ? 'NH3-N' : p.indicator === 'suspended_solids' ? 'SS' : p.indicator,
      side: p.side, plant, start: vc.segmentStart, end: vc.segmentEnd,
      source,
    })
    if (disposed || route.path !== '/dashboard' || store.activePlant !== plant || store.dashboard?.data_context?.bucket !== source || actionStore.viewContext.segmentStart !== vc.segmentStart || actionStore.viewContext.segmentEnd !== vc.segmentEnd) return { success: false, code: 'stale_context', message: '检测期间页面、来源或采样窗口已变化，未应用旧标注' }
    const annotations = response.data?.actionData?.annotations
    if (!response.success || response.data?.status !== 'completed' || !Array.isArray(annotations) || annotations.some(a => typeof a.timestamp !== 'string' || typeof a.value !== 'number' || !Number.isFinite(a.value) || typeof a.type !== 'string')) return { success: false, message: response.error || '检测没有返回可核验的完成结果' }
    if (!response.data.execution_context || Object.entries(expected).some(([key, value]) => response.data!.execution_context![key] !== value)) return { success: false, code: 'binding_mismatch', message: '检测返回的执行对象或时段不一致，未应用标注' }
    if (!boardRef.value?.applyAssistantAnnotations) return { success: false, code: 'chart_not_ready', message: '目标图表尚未就绪，检测结果未应用' }
    return await boardRef.value.applyAssistantAnnotations(annotations, { plant, source, start: vc.segmentStart, end: vc.segmentEnd, indicator: String(p.indicator), side: p.side as 'influent' | 'effluent', algorithm: String(p.algorithm), timezone: store.dashboard?.data_context?.timezone })
  }
  if (typeof p.plant === 'string') {
    // Capture the target-page lease here, after any executor navigation.
    const lease = assistantContext.snapshot()
    const plant = store.activePlant
    await store.fetchTree()
    const changed = contextPolicy(action, lease as unknown as Record<string, unknown>, assistantContext.current as unknown as Record<string, unknown>)
    if (disposed || route.path !== '/dashboard' || changed || store.activePlant !== plant) return { success: false, code: 'stale_context', message: changed || '页面或厂站已变化，未应用旧操作' }
    const ids = [...(store.tree?.cities.flatMap(c => c.districts.flatMap(d => d.plants.map(v => v.plant_id))) || []), ...(store.tree?.ungrouped.map(v => v.plant_id) || [])]
    if (!ids.includes(p.plant)) return { success: false, message: '厂站不在已加载目录中' }
    store.selectPlant(p.plant)
  }
  tab.value = 'dash'
  if (action.capability === 'dashboard.view') actionStore.dispatch({ cmd: 'set_view', indicators: p.indicator ? [String(p.indicator)] : undefined, side: p.side as 'influent' | 'effluent' | 'all' | undefined })
  else {
    await nextTick()
    const range = p.range as '1h' | '6h' | '24h' | '7d' | '30d'
    const success = await boardRef.value?.applyAssistantRange(range)
    if (!success) return { success: false, message: store.dashboardError || '大屏数据尚未就绪，未完成时间切换' }
    actionStore.dispatch({ cmd: 'set_time_range', range })
    return { success: true, message: `大屏已加载 ${range} 采样窗口` }
  }
  return { success: true, message: '大屏显示条件已更新；采样加载状态请查看大屏' }
})
</script>

<style scoped>
.dash-page { display: flex; flex-direction: column; gap: 14px }
.top-tabs { display: flex; gap: 4px; background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 11px; padding: 4px; width: fit-content }
.top-tabs button { all: unset; cursor: pointer; font-size: 13px; padding: 7px 18px; border-radius: 8px;
  color: var(--text-secondary, #475569); transition: background .15s }
.top-tabs button:hover { background: var(--primary-light, #eef2ff) }
.top-tabs button.on { background: linear-gradient(135deg, var(--cyan, #22d3ee), #5fb9ff);
  color: #04121a; font-weight: 700 }
.dash-layout { display: flex; gap: 16px; align-items: flex-start; min-height: 0 }
.dash-side { width: 200px; flex-shrink: 0; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 10px 8px }
.dash-side-ttl { font-size: 11px; color: var(--text-muted, #94a3b8); letter-spacing: .5px;
  padding: 2px 6px 8px }
.dash-main { flex: 1; min-width: 0 }
@media (max-width: 800px) { .dash-side { width: 150px } }

.placeholder { padding: 90px 20px; text-align: center; color: var(--text-muted);
  background: var(--card-bg, #fff); border: 1px dashed var(--brd, #e2e8f0); border-radius: 13px }
.ph-ico { font-size: 40px; margin-bottom: 10px }
.ph-t { font-size: 15px; font-weight: 600; color: var(--text-secondary) }
.ph-d { font-size: 12.5px; margin-top: 6px }
</style>
