// frontend/src/stores/knowledge.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { knowledgeService } from '@/api/modules/knowledge'
import type { KGNode, KGEdge, KGStats } from '@/api/modules/knowledge'

// 节点类型元数据：中文标签/颜色/tab 归属（domain=领域知识 / topology=服务拓扑）。
// tab 是数组：operator 双归属（spec L66）——domain 里是检测器，topology 里是 shared 算子库成员（使 employs 边可见）
// 颜色经 dataviz 校验器验证（light 面 全 PASS）：降饱和去塑料感；viol红独占暖区语义色；
// protan 最差对 7.2 在合法带内，靠节点文字标签做辅助编码（图上节点均带 label，天然满足）
export const NODE_META: Record<string, { label: string; color: string; tab: ('domain' | 'topology')[] }> = {
  library: { label: '库', color: '#0f172a', tab: ['domain'] },
  category: { label: '分类', color: '#475569', tab: ['domain'] },
  plant: { label: '厂区', color: '#3b82f6', tab: ['domain'] },
  indicator: { label: '指标', color: '#15876b', tab: ['domain'] },
  violation_pattern: { label: '违规模式', color: '#b91c1c', tab: ['domain'] },
  operator: { label: '算子', color: '#eb6834', tab: ['domain', 'topology'] },
  regulation: { label: '法规', color: '#5b21b6', tab: ['domain'] },
  case: { label: '案例', color: '#a52a8a', tab: ['domain'] },
  agent: { label: '智能体', color: '#3b82f6', tab: ['topology'] },
  service: { label: '服务', color: '#15876b', tab: ['topology'] },
}

/** 当前可见类型 = tab 预设 - hidden（hidden 为反向集合：空=全显，取消勾选即加入） */
export function computeVisibleTypes(tab: 'domain' | 'topology', hidden: string[]): string[] {
  return Object.keys(NODE_META)
    .filter(k => NODE_META[k].tab.includes(tab) && !hidden.includes(k))
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
  /** 度数（边数）——尺寸编码用：度数越高节点越大，图有层级不再是均匀点阵 */
  degree: number
  symbolSize: number
  itemStyle: { color: string | undefined }
  /** 高连接度枢纽节点：标签常显；叶子节点标签 hover 才显（label:show 由 view 控制） */
  hub: boolean
}
export interface GraphLinkDatum {
  source: string
  target: string
  value: string
}

/** 尺寸映射：库/分类层级节点有基础大尺寸（层级感不靠度数——库是顶层枢纽）；
 * 其余按度数：10px（孤立点）~ 52px（枢纽），开方让中小度数差异更可感 */
function degreeSize(degree: number, isTopologyCore: boolean, type?: string): number {
  if (type === 'library') return 56
  if (type === 'category') return 40
  const base = 8 + Math.sqrt(degree) * 10
  return Math.min(52, isTopologyCore ? base + 6 : base)
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
  // 度数统计（只数可见边——过滤后图例会让度数随子图重算）
  const degree = new Map<string, number>()
  const visSet = new Set(vis)
  const nodesById = new Map(nodes.map(n => [n.id, n]))
  for (const e of edges) {
    const s = nodesById.get(e.src); const d = nodesById.get(e.dst)
    if (!s || !d || !visSet.has(s.type) || !visSet.has(d.type)) continue
    degree.set(e.src, (degree.get(e.src) ?? 0) + 1)
    degree.set(e.dst, (degree.get(e.dst) ?? 0) + 1)
  }
  // 度数中位数：hub 判定基准（相对值，图大小变化仍成立）
  const degs = [...degree.values()].sort((a, b) => a - b)
  const medianDeg = degs.length ? degs[Math.floor(degs.length / 2)] : 0
  const data: GraphNodeDatum[] = nodes
    .filter(n => vis.includes(n.type))
    .map(n => {
      const deg = degree.get(n.id) ?? 0
      return {
        id: n.id,
        name: n.label,
        category: catIdx.get(n.type) ?? 0,
        degree: deg,
        symbolSize: degreeSize(deg, NODE_META[n.type]?.tab.includes('topology') ?? false, n.type),
        itemStyle: { color: NODE_META[n.type]?.color },
        hub: deg > Math.max(medianDeg, 2),
      }
    })
  const nodeIds = new Set(data.map(d => d.id))
  const links: GraphLinkDatum[] = edges
    .filter(e => nodeIds.has(e.src) && nodeIds.has(e.dst))
    .map(e => ({ source: e.src, target: e.dst, value: e.type }))
  return { data, links, categories }
}
