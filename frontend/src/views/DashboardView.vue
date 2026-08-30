<template>
  <div class="dash-page">
    <!-- 顶部：三个可切换选项卡（参考 aiops.hgdz.cn：仪表盘/系统态势/态势历史） -->
    <div class="top-tabs">
      <button v-for="t in TOP_TABS" :key="t.v" :class="{ on: tab === t.v }" @click="tab = t.v">{{ t.t }}</button>
    </div>

    <!-- 仪表盘 tab：看板列表(市→厂区→厂) + 选中厂流式看板 -->
    <div v-if="tab === 'dash'" class="dash-layout">
      <div class="dash-side">
        <div class="dash-side-ttl">看板列表</div>
        <PlantTree @select="onPickPlant" />
      </div>
      <div class="dash-main">
        <PlantBoardPanel v-if="store.activePlant" :key="store.activePlant" :plant-id="store.activePlant" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePlantsStore } from '@/stores/plants'
import { useActionStore } from '@/stores/action'
import PlantTree from '@/components/cockpit/PlantTree.vue'
import PlantBoardPanel from '@/views/PlantBoardPanel.vue'
import SystemStatusView from '@/views/SystemStatusView.vue'
import SituationHistoryView from '@/views/SituationHistoryView.vue'

// 顶部三个选项卡（同参考站：仪表盘 / 系统态势 / 态势历史）
const TOP_TABS = [
  { t: '仪表盘', v: 'dash' }, { t: '系统态势', v: 'sys' }, { t: '态势历史', v: 'hist' },
] as const
const tab = ref<'dash' | 'sys' | 'hist'>('dash')

const store = usePlantsStore()

function onPickPlant(pid: string) {
  store.selectPlant(pid)  // 记选中（父级链展开由 PlantTree 内部处理）
}

// 首次进入：自动选中第一棵树第一个厂（树加载完后）
store.fetchTree().then((t) => {
  if (!store.activePlant && t) {
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
.dash-layout { display: flex; gap: 16px; align-items: flex-start }
.dash-side { width: 200px; flex-shrink: 0; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 10px 8px }
.dash-side-ttl { font-size: 11px; color: var(--text-muted, #94a3b8); letter-spacing: .5px;
  padding: 2px 6px 8px }
.dash-main { flex: 1; min-width: 0 }

.placeholder { padding: 90px 20px; text-align: center; color: var(--text-muted);
  background: var(--card-bg, #fff); border: 1px dashed var(--brd, #e2e8f0); border-radius: 13px }
.ph-ico { font-size: 40px; margin-bottom: 10px }
.ph-t { font-size: 15px; font-weight: 600; color: var(--text-secondary) }
.ph-d { font-size: 12.5px; margin-top: 6px }
</style>
