<!-- frontend/src/views/AgentConfigView.vue -->
<template>
  <div class="cfg">
    <!-- 第一级导航：实体横排（主智能体/4子智能体/技能/MCP/供应商/厂区配置/服务管理）
         MCP 与供应商是全局能力(只服务主智能体进程)，提到一级——不挂在某个实体下 -->
    <div class="nav-entities">
      <button v-for="e in navItems" :key="e.name" class="nav-e"
              :class="{ active: activeEntity === e.name }" @click="switchEntity(e.name)">
        <span class="nav-icon">{{ e.icon }}</span>{{ e.label }}
      </button>
    </div>
    <!-- 第二级导航：智能体实体的 tab（MCP/供应商已提一级，这里不再出现） -->
    <div class="tabs" v-if="isEntity">
      <button v-for="t in tabsFor" :key="t" class="tab"
              :class="{ active: tab === t }" @click="switchTab(t)">
        {{ TAB_LABELS[t] }}
      </button>
    </div>
    <div class="cfg-body" :class="{ 'no-tab': !isEntity }">
      <EntityOverview v-if="isEntity && tab === 'overview' && currentEntity"
                      :entity="currentEntity" @openFile="openFileFromOverview" />
      <div v-else-if="isEntity && tab === 'files'" class="files-wrap">
        <IdentityFileEditor v-if="currentEntity" :entity="currentEntity" ref="editorRef" />
      </div>
      <SkillsPanel v-else-if="isEntity && tab === 'skills'" :entity="activeEntity" />
      <StrategyPanel v-else-if="isEntity && tab === 'strategy'" @restart="goRestart" />
      <McpPanel v-else-if="activeEntity === '__mcp__'" @restart="goRestart" />
      <ProvidersPanel v-else-if="activeEntity === '__providers__'" @restart="goRestart" />
      <PlantsConfigPanel v-else-if="activeEntity === '__plants__'" />
      <ServiceControl v-else-if="activeEntity === '__service__'" />
      <div v-else class="loading">加载中…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentConfigService, type AgentEntity } from '@/api/modules/agentConfig'
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
    ? ['overview', 'files', 'skills', 'strategy']
    : ['overview', 'files', 'skills', 'strategy'])

// 顶部一级导航项 = 5 个智能体实体 + MCP/供应商（全局能力）+ 厂区 + 服务
const navItems = computed(() => [
  ...(entities.value as AgentEntity[]),
  { name: '__mcp__', label: 'MCP', icon: '🔌' },
  { name: '__providers__', label: '供应商', icon: '🌐' },
  { name: '__plants__', label: '厂区配置', icon: '⚙️' },
  { name: '__service__', label: '服务管理', icon: '🔄' },
])

// 一级直达入口（无二级 tab）
const DIRECT_ENTITIES = ['__mcp__', '__providers__', '__plants__', '__service__']

function switchEntity(name: string) {
  if (activeEntity.value === name) return
  if (tab.value === 'files' && editorRef.value?.dirty) {
    if (!confirm('有未保存的编辑，切换将丢失，确定？')) return
  }
  activeEntity.value = name
}

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
    if (!isEntity.value && q.entity && !DIRECT_ENTITIES.includes(q.entity)) {
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
.cfg { display: flex; flex-direction: column; height: calc(100vh - 110px);
  background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  overflow: hidden; box-shadow: var(--card-shadow) }
/* 一级：实体横排导航 */
.nav-entities { display: flex; align-items: center; gap: 2px; padding: 8px 14px 0;
  border-bottom: 1px solid var(--brd); background: #f8fafc; overflow-x: auto }
.nav-e { display: inline-flex; align-items: center; gap: 7px; border: none; background: none;
  font-size: 13.5px; color: var(--text-secondary); padding: 9px 15px; cursor: pointer;
  border-bottom: 2px solid transparent; margin-bottom: -1px; white-space: nowrap;
  border-radius: 8px 8px 0 0 }
.nav-e:hover { color: var(--primary); background: #eef2ff55 }
.nav-e.active { color: var(--primary); font-weight: 700; border-bottom-color: var(--primary);
  background: var(--card-bg) }
.nav-icon { font-size: 15px }
/* 二级：tab */
.tabs { display: flex; gap: 4px; padding: 8px 16px 0; border-bottom: 1px solid var(--brd) }
.tab { border: none; background: none; font-size: 12.5px; color: var(--text-secondary);
  padding: 6px 13px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px }
.tab.active { color: var(--primary); font-weight: 600; border-bottom-color: var(--primary) }
.cfg-body { flex: 1; overflow: auto; padding: 18px }
.cfg-body.no-tab { border-top: 1px solid var(--brd) }
.files-wrap { height: 100% }
.loading { color: var(--text-muted); padding: 40px; text-align: center }
</style>
