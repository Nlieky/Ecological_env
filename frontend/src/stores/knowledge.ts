// frontend/src/stores/knowledge.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { knowledgeService } from '@/api/modules/knowledge'
import type { KGNode, KGEdge, KGStats } from '@/api/modules/knowledge'

// 节点类型元数据：中文标签/颜色/tab 归属（domain=领域知识 / topology=服务拓扑）
export const NODE_META: Record<string, { label: string; color: string; tab: 'domain' | 'topology' }> = {
  plant: { label: '厂区', color: '#22c55e', tab: 'domain' },
  indicator: { label: '指标', color: '#84cc16', tab: 'domain' },
  violation_pattern: { label: '违规模式', color: '#ef4444', tab: 'domain' },
  operator: { label: '算子', color: '#f59e0b', tab: 'domain' },
  regulation: { label: '法规', color: '#8b5cf6', tab: 'domain' },
  case: { label: '案例', color: '#ec4899', tab: 'domain' },
  agent: { label: '智能体', color: '#3b82f6', tab: 'topology' },
  service: { label: '服务', color: '#06b6d4', tab: 'topology' },
}

export const useKnowledgeStore = defineStore('knowledge', () => {
  const allNodes = ref<KGNode[]>([])
  const allEdges = ref<KGEdge[]>([])
  const stats = ref<KGStats | null>(null)
  const seeded = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeTab = ref<'domain' | 'topology'>('domain')
  const enabledTypes = ref<string[]>([]) // 空=该 tab 全选

  async function loadGraph() {
    loading.value = true
    error.value = null
    try {
      const resp = await knowledgeService.graph()
      allNodes.value = resp.nodes
      allEdges.value = resp.edges
      stats.value = resp.stats
      seeded.value = resp.seeded
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  function toggleType(t: string) {
    enabledTypes.value = enabledTypes.value.includes(t)
      ? enabledTypes.value.filter(x => x !== t)
      : [...enabledTypes.value, t]
  }

  /** 当前可见类型 = tab 预设 ∩ 图例勾选（勾选为空=全选 tab 预设） */
  const visibleTypes = computed(() => {
    const tabTypes = Object.keys(NODE_META).filter(
      k => NODE_META[k].tab === activeTab.value)
    if (!enabledTypes.value.length) return tabTypes
    return tabTypes.filter(t => enabledTypes.value.includes(t))
  })

  /** 切 tab 时重置图例勾选 */
  function setTab(tab: 'domain' | 'topology') {
    activeTab.value = tab
    enabledTypes.value = []
  }

  const selectedNode = ref<KGNode | null>(null)
  const selectedNeighbors = ref<Record<string, KGNode[]>>({})
  async function selectNode(id: string) {
    try {
      const resp = await knowledgeService.node(id)
      selectedNode.value = resp.node
      selectedNeighbors.value = resp.neighbors
    } catch {
      selectedNode.value = null
    }
  }
  function clearSelection() {
    selectedNode.value = null
    selectedNeighbors.value = {}
  }

  return { allNodes, allEdges, stats, seeded, loading, error,
           activeTab, enabledTypes, visibleTypes, toggleType, setTab,
           selectedNode, selectedNeighbors, selectNode, clearSelection, loadGraph }
})

/** nodes/edges + 可见类型集合 → ECharts graph series（data/links/categories） */
export function toEChartsSeries(
  nodes: KGNode[], edges: KGEdge[], visibleTypes: string[],
): { data: unknown[]; links: unknown[]; categories: { name: string }[] } {
  const vis = visibleTypes.slice() // 保持顺序=categories 顺序
  const categories = vis.map(t => ({ name: NODE_META[t]?.label ?? t }))
  const catIdx = new Map(vis.map((t, i) => [t, i]))
  const data = nodes
    .filter(n => vis.includes(n.type))
    .map(n => ({
      id: n.id,
      name: n.label,
      category: catIdx.get(n.type) ?? 0,
      symbolSize: n.type === 'agent' || n.type === 'service' ? 40 : 28,
      itemStyle: { color: NODE_META[n.type]?.color },
    }))
  const nodeIds = new Set(data.map(d => (d as { id: string }).id))
  const links = edges
    .filter(e => nodeIds.has(e.src) && nodeIds.has(e.dst))
    .map(e => ({ source: e.src, target: e.dst, value: e.type }))
  return { data, links, categories }
}
