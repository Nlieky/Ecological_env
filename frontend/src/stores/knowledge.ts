// frontend/src/stores/knowledge.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { knowledgeService } from '@/api/modules/knowledge'
import type { KGNode, KGEdge, KGStats, ImpactEntry, ImpactResp } from '@/api/modules/knowledge'

// 节点类型元数据：中文标签/颜色/tab 归属（domain=领域知识 / topology=服务拓扑）。
// tab 是数组：operator 双归属（spec L66）——domain 里是检测器，topology 里是 shared 算子库成员（使 employs 边可见）
// 颜色经 dataviz 校验器验证（light 面 全 PASS）：降饱和去塑料感；viol红独占暖区语义色；
// protan 最差对 7.2 在合法带内，靠节点文字标签做辅助编码（图上节点均带 label，天然满足）
export const NODE_META: Record<string, { label: string; color: string; tab: ('domain' | 'topology')[] }> = {
  library: { label: '库', color: '#0f172a', tab: ['domain', 'topology'] },
  // category 双归属：拓扑 tab 里算子→分类→库 的归属树让 38 个算子不再是孤环
  // （只给 library 双 tab 时 belongs_to 边的 category 端不可见，边被两端规则滤掉）
  category: { label: '分类', color: '#475569', tab: ['domain', 'topology'] },
  knowledge_doc: { label: '知识文档', color: '#64748b', tab: ['domain'] },
  plant: { label: '厂区', color: '#3b82f6', tab: ['domain'] },
  indicator: { label: '指标', color: '#15876b', tab: ['domain'] },
  violation_pattern: { label: '违规模式', color: '#b91c1c', tab: ['domain'] },
  // 算子只在领域 tab：38个算子的归属树归"领域知识"管；拓扑 tab 里"哪个智能体
  // 用什么算子"已由技能层（uses 边）承载，重复展示反而挤占拓扑画布。
  // employs 边（agent→算子）随之只在领域 tab 可见（两端规则自动滤）。
  operator: { label: '算子', color: '#eb6834', tab: ['domain'] },
  regulation: { label: '法规', color: '#5b21b6', tab: ['domain'] },
  case: { label: '案例', color: '#a52a8a', tab: ['domain'] },
  agent: { label: '智能体', color: '#3b82f6', tab: ['topology'] },
  service: { label: '服务', color: '#15876b', tab: ['topology'] },
  skill: { label: '技能', color: '#7c3aed', tab: ['topology'] },
  tool: { label: '工具', color: '#0369a1', tab: ['topology'] },
  // MCP 用冷灰蓝：与已撤出拓扑tab的算子橙色(#eb6834)拉开,防"MCP 误读成算子残留"
  mcp: { label: 'MCP', color: '#64748b', tab: ['topology'] },
}

/** 当前可见类型 = tab 预设 - hidden（hidden 为反向集合：空=全显，取消勾选即加入） */
export function computeVisibleTypes(tab: 'domain' | 'topology', hidden: string[]): string[] {
  return Object.keys(NODE_META)
    .filter(k => NODE_META[k].tab.includes(tab) && !hidden.includes(k))
}

/** 影响推演结果（子项目4 根因分析）：fault=起点，downstream=波及，upstream=根因候选 */
export interface ImpactResult {
  nodeId: string
  node: KGNode | null
  downstream: ImpactEntry[]
  upstream: ImpactEntry[]
}

export type ImpactState = 'fault' | 'affected' | 'candidate' | 'unrelated' | 'normal'

/** 推演着色三色：fault 红 / affected 橙（波及）/ candidate 紫（根因候选） */
export const IMPACT_COLORS: Record<'fault' | 'affected' | 'candidate', string> = {
  fault: '#ef4444', affected: '#f97316', candidate: '#8b5cf6',
}

/** 节点在推演结果中的角色（纯函数，视图据此叠加着色/透明度） */
export function impactNodeStyle(
  id: string, result: ImpactResult | null,
): { state: ImpactState; color?: string } {
  if (!result) return { state: 'normal' }
  if (id === result.nodeId) return { state: 'fault', color: IMPACT_COLORS.fault }
  if (result.downstream.some(e => e.id === id)) return { state: 'affected', color: IMPACT_COLORS.affected }
  if (result.upstream.some(e => e.id === id)) return { state: 'candidate', color: IMPACT_COLORS.candidate }
  return { state: 'unrelated' }
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

  /** 切 tab 时重置图例勾选 + 退出推演（领域 tab 无服务拓扑，推演无意义） */
  function setTab(tab: 'domain' | 'topology') {
    activeTab.value = tab
    hiddenTypes.value = []
    impactMode.value = false
    impactResult.value = null
  }

  // ── 影响推演状态机（子项目4）──
  const impactMode = ref(false) // 开关：开=点节点做推演而非打开详情
  const impactResult = ref<ImpactResult | null>(null)
  // API 注入口（ref 才能让 store._impactApi = mock 经 pinia 代理写进闭包可见的引用）
  const _impactApi = ref<(id: string) => Promise<ImpactResp>>(
    (id: string) => knowledgeService.impact(id))

  async function runImpact(id: string) {
    try {
      const resp = await _impactApi.value(id)
      impactResult.value = {
        nodeId: id, node: resp.node, downstream: resp.downstream, upstream: resp.upstream,
      }
      impactMode.value = true
    } catch {
      // 失败置空结果但不退模式——用户可直接再点（不强制回详情交互）
      impactResult.value = null
      ElMessage.error('推演失败')
    }
  }
  function clearImpact() {
    impactMode.value = false
    impactResult.value = null
  }
  function toggleImpactMode() {
    impactMode.value = !impactMode.value
    // 任何模式切换都清残留结果：关时清着色/摘要条；开时清上次会话残留（真实流程
    // 里 result 只在开模式下存在，开向清除是无害兜底——直接改状态后切换也不留旧色）
    impactResult.value = null
  }

  /** 60s 慢轮询：重拉全图但只把 service 节点的 health 合并回 allNodes（其余原对象不动） */
  async function refreshHealth() {
    const resp = await knowledgeService.graph(undefined, true)
    const healthById = new Map<string, { health: unknown; checked_at: unknown }>()
    for (const n of resp.nodes) {
      if (n.type === 'service' && n.props && 'health' in n.props) {
        healthById.set(n.id, {
          health: n.props.health,
          checked_at: n.props.health_checked_at ?? '',
        })
      }
    }
    if (!healthById.size) return
    // 局部替换 map（新数组引用触发视图重渲染 watch；非 service 节点对象原样保留）
    allNodes.value = allNodes.value.map(n => {
      const h = healthById.get(n.id)
      return h ? { ...n, props: { ...n.props, health: h.health, health_checked_at: h.checked_at } } : n
    })
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
           selectedNode, selectedNeighbors, selectNode, clearSelection, loadGraph,
           impactMode, impactResult, _impactApi, runImpact, clearImpact,
           toggleImpactMode, refreshHealth }
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
