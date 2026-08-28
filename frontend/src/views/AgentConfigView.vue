<!-- frontend/src/views/AgentConfigView.vue -->
<template>
  <div class="cfg">
    <EntityTree v-if="entities.length" :entities="entities" v-model="activeEntity" />
    <div class="cfg-main">
      <div class="tabs" v-if="isEntity">
        <button v-for="t in tabsFor" :key="t" class="tab"
                :class="{ active: tab === t }" @click="switchTab(t)">
          {{ TAB_LABELS[t] }}
        </button>
      </div>
      <div class="cfg-body">
        <EntityOverview v-if="isEntity && tab === 'overview' && currentEntity"
                        :entity="currentEntity" @openFile="openFileFromOverview" />
        <div v-else-if="isEntity && tab === 'files'" class="files-wrap">
          <IdentityFileEditor v-if="currentEntity" :entity="currentEntity" ref="editorRef" />
        </div>
        <SkillsPanel v-else-if="isEntity && tab === 'skills'" :entity="activeEntity" />
        <StrategyPanel v-else-if="isEntity && tab === 'strategy'" @restart="goRestart" />
        <McpPanel v-else-if="isEntity && tab === 'mcp'" @restart="goRestart" />
        <ProvidersPanel v-else-if="isEntity && tab === 'providers'" @restart="goRestart" />
        <PlantsConfigPanel v-else-if="activeEntity === '__plants__'" />
        <ServiceControl v-else-if="activeEntity === '__service__'" />
        <div v-else class="loading">加载中…</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentConfigService, type AgentEntity } from '@/api/modules/agentConfig'
import EntityTree from '@/components/agents/config/EntityTree.vue'
import EntityOverview from '@/components/agents/config/EntityOverview.vue'
import IdentityFileEditor from '@/components/agents/config/IdentityFileEditor.vue'
import SkillsPanel from '@/components/agents/config/SkillsPanel.vue'
import StrategyPanel from '@/components/agents/config/StrategyPanel.vue'
import McpPanel from '@/components/agents/config/McpPanel.vue'
import ProvidersPanel from '@/components/agents/config/ProvidersPanel.vue'
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
import ServiceControl from '@/components/agents/config/ServiceControl.vue'

const TAB_LABELS: Record<string, string> = {
  overview: '概览', files: '身份文件', skills: '技能',
  strategy: '策略', mcp: 'MCP', providers: '供应商',
}
const route = useRoute()
const router = useRouter()

const entities = ref<AgentEntity[]>([])
const activeEntity = ref('master')
const tab = ref('overview')
const editorRef = ref()

const isEntity = computed(() => entities.value.some(e => e.name === activeEntity.value))
const currentEntity = computed(() => entities.value.find(e => e.name === activeEntity.value))
const tabsFor = computed(() =>
  activeEntity.value === 'master'
    ? ['overview', 'files', 'skills', 'strategy', 'mcp', 'providers']
    : ['overview', 'files', 'skills', 'strategy'])

function switchTab(t: string) {
  if (tab.value === 'files' && t !== 'files' && editorRef.value?.dirty) {
    if (!confirm('有未保存的编辑，切换将丢失，确定？')) return
  }
  tab.value = t
  router.replace({ query: { ...route.query, tab: t } })
}

async function openFileFromOverview(f: string) {
  tab.value = 'files'
  router.replace({ query: { ...route.query, tab: 'files' } })
  // v-if 切换后 ref 异步绑定，nextTick 兜底再调 editor 的 openFile
  await nextTick()
  editorRef.value?.openFile(f)
}

function goRestart() { activeEntity.value = '__service__' }

// URL → 状态（首载/刷新/分享链接保形）
onMounted(async () => {
  const q = route.query as Record<string, string>
  if (q.entity) activeEntity.value = q.entity
  if (q.tab) tab.value = q.tab
  try {
    const r: any = await agentConfigService.entities()
    entities.value = (r.data ?? r) as AgentEntity[]
    if (!isEntity.value && q.entity && q.entity !== '__plants__' && q.entity !== '__service__') {
      activeEntity.value = 'master'   // 非法 entity 回落
    }
    // tab 与实体不匹配（如子智能体选了 mcp）回落 overview
    if (isEntity.value && !tabsFor.value.includes(tab.value)) tab.value = 'overview'
  } catch { /* 各面板自行处理 */ }
})

// 实体切换 → URL 同步 + tab 合法性
watch(activeEntity, (v) => {
  router.replace({ query: { ...route.query, entity: v } })
  if (isEntity.value && !tabsFor.value.includes(tab.value)) tab.value = 'overview'
})
</script>

<style scoped>
.cfg { display: flex; height: calc(100vh - 110px); background: var(--card-bg);
  border: 1px solid var(--brd); border-radius: 13px; overflow: hidden;
  box-shadow: var(--card-shadow) }
.cfg-main { flex: 1; min-width: 0; display: flex; flex-direction: column }
.tabs { display: flex; gap: 4px; padding: 10px 16px 0; border-bottom: 1px solid var(--brd) }
.tab { border: none; background: none; font-size: 13px; color: var(--text-secondary);
  padding: 7px 14px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px }
.tab.active { color: var(--primary); font-weight: 600; border-bottom-color: var(--primary) }
.cfg-body { flex: 1; overflow: auto; padding: 18px }
.files-wrap { height: 100% }
.loading { color: var(--text-muted); padding: 40px; text-align: center }
</style>
