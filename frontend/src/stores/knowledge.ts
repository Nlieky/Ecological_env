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

/** 当前可见类型 = tab 预设 - hidden（hidden 为反向集合：空=全显，取消勾选即加入） */
export function computeVisibleTypes(tab: 'domain' | 'topology', hidden: string[]): string[] {
  return Object.keys(NODE_META)
    .filter(k => NODE_META[k].tab === tab && !hidden.includes(k))
}

export const useKnowledgeStore = defineStore('knowledge', () => {
  const allNodes = ref<KGNode[]>([])
  const allEdges = ref<KGEdge[]>([])
  const stats = ref<KGStats | null>(null)
  const seeded = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeTab = ref<'domain' | 'topology'>('domain')
  const hiddenTypes = ref<string[]>([]) // 空=该 tab 全显

  async function loadGraph() {
    if (loading.value) return // 防重入
    loading.value = true
    error.value = null
    try {
      const resp = await knowledgeService.graph()
      allNodes.value = resp.nodes
      allEdges.value = resp.edges
      stats.value = resp.stats
      seeded.value = resp.seeded
    } catch (e: any) {
      error.value = e?.message || '知识图谱加载失败'
    } finally {
      loading.value = false
    }
  }

  function toggleType(t: string) {
    hiddenTypes.value = hiddenTypes.value.includes(t)
      ? hiddenTypes.value.filter(x => x !== t)
      : [...hiddenTypes.value, t]
  }

  const visibleTypes = computed(() => computeVisibleTypes(activeTab.value, hiddenTypes.value))

  /** 切 tab 时重置图例勾选 */
  function setTab(tab: 'domain' | 'topology') {
    activeTab.value = tab
    hiddenTypes.value = []
  }

  const selectedNode = ref<KGNode | null>(null)
  const selectedNeighbors = ref<Record<string, KGNode[]>>({})
  async function selectNode(id: string) {
    try {
      const resp = await knowledgeService.node(id)
      selectedNode.value = resp.node
      selectedNeighbors.value = resp.neighbors
    } catch (e: any) {
      selectedNode.value = null
      selectedNeighbors.value = {} // 失败对称清空——不留上一节的过期邻居
      error.value = e?.message || '节点详情加载失败'
    }
  }
  function clearSelection() {
    selectedNode.value = null
    selectedNeighbors.value = {}
  }

  return { allNodes, allEdges, stats, seeded, loading, error,
           activeTab, hiddenTypes, visibleTypes, toggleType, setTab,
           selectedNode, selectedNeighbors, selectNode, clearSelection, loadGraph }
})

/** ECharts graph series 节点/边数据形状 */
export interface GraphNodeDatum {
  id: string
  name: string
  category: number
  symbolSize: number
  itemStyle: { color: string | undefined }
}
export interface GraphLinkDatum {
  source: string
  target: string
  value: string
}

/** nodes/edges + 可见类型集合 → ECharts graph series（data/links/categories） */
export function toEChartsSeries(
  nodes: KGNode[], edges: KGEdge[], visibleTypes: string[],
): {
  data: GraphNodeDatum[]
  links: GraphLinkDatum[]
  categories: { name: string; itemStyle: { color: string | undefined } }[]
} {
  const vis = visibleTypes.slice() // 保持顺序=categories 顺序
  const categories = vis.map(t => ({
    name: NODE_META[t]?.label ?? t,
    // ECharts 图例(legend)从 category.itemStyle 取色——必须与节点颜色一致
    itemStyle: { color: NODE_META[t]?.color },
  }))
  const catIdx = new Map(vis.map((t, i) => [t, i]))
  const data: GraphNodeDatum[] = nodes
    .filter(n => vis.includes(n.type))
    .map(n => ({
      id: n.id,
      name: n.label,
      category: catIdx.get(n.type) ?? 0,
      symbolSize: NODE_META[n.type]?.tab === 'topology' ? 40 : 28,
      itemStyle: { color: NODE_META[n.type]?.color },
    }))
  const nodeIds = new Set(data.map(d => d.id))
  const links: GraphLinkDatum[] = edges
    .filter(e => nodeIds.has(e.src) && nodeIds.has(e.dst))
    .map(e => ({ source: e.src, target: e.dst, value: e.type }))
  return { data, links, categories }
}
