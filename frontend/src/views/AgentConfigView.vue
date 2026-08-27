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
        <ParamsPanel v-else-if="isEntity && tab === 'params'" @restart="goRestart" />
        <PlantsConfigPanel v-else-if="activeEntity === '__plants__'" />
        <ServiceControl v-else-if="activeEntity === '__service__'" />
        <div v-else class="loading">加载中…</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { agentConfigService, type AgentEntity } from '@/api/modules/agentConfig'
import EntityTree from '@/components/agents/config/EntityTree.vue'
import EntityOverview from '@/components/agents/config/EntityOverview.vue'
import IdentityFileEditor from '@/components/agents/config/IdentityFileEditor.vue'
import ParamsPanel from '@/components/agents/config/ParamsPanel.vue'
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
import ServiceControl from '@/components/agents/config/ServiceControl.vue'

const entities = ref<AgentEntity[]>([])
const activeEntity = ref('master')
const tab = ref('overview')
const editorRef = ref()

const TAB_LABELS: Record<string, string> = { overview: '概览', files: '身份文件', params: '运行参数' }
const tabsFor = computed(() =>
  activeEntity.value === 'master' ? ['overview', 'files', 'params'] : ['overview', 'files'])

const isEntity = computed(() => entities.value.some(e => e.name === activeEntity.value))
const currentEntity = computed(() => entities.value.find(e => e.name === activeEntity.value))

function switchTab(t: string) {
  if (tab.value === 'files' && t !== 'files' && editorRef.value?.dirty) {
    if (!confirm('有未保存的编辑，切换将丢失，确定？')) return
  }
  tab.value = t
}

async function openFileFromOverview(f: string) {
  tab.value = 'files'
  // v-if 切换后 ref 异步绑定，nextTick 兜底再调 editor 的 openFile
  await nextTick()
  editorRef.value?.openFile(f)
}

function goRestart() { activeEntity.value = '__service__' }

onMounted(async () => {
  try {
    const r: any = await agentConfigService.entities()
    entities.value = (r?.data ?? r) as AgentEntity[]
  } catch { /* 各面板自行处理错误 */ }
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
