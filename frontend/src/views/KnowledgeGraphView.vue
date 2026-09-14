<template>
  <div class="kg-page">
    <!-- 页面级顶部导航栏：左标题+副标题，中 tab，右搜索+图例开关+重置 -->
    <div class="kg-navbar">
      <div class="kg-navbar-left">
        <div class="kg-navbar-title">
          <span class="kg-navbar-name">知识图谱</span>
          <span class="kg-navbar-sub">厂区 · 指标 · 违规模式 · 算子 · 法规 关系地图</span>
        </div>
        <el-radio-group :model-value="store.activeTab" size="small" @update:model-value="store.setTab">
          <el-radio-button value="domain">领域知识</el-radio-button>
          <el-radio-button value="topology">服务拓扑</el-radio-button>
        </el-radio-group>
      </div>
      <div class="kg-navbar-right">
        <!-- 影响推演开关（仅服务拓扑 tab：推演在拓扑边集上流动，领域 tab 无意义） -->
        <button v-if="store.activeTab === 'topology'" type="button" class="kg-tool"
                :class="{ on: store.impactMode }"
                title="开启后点击节点推演故障影响面：波及谁 / 可能由谁引起"
                @click="store.toggleImpactMode">
          <span class="kg-bolt">⚡</span> 影响推演
        </button>
        <el-select v-model="searchId" filterable clearable placeholder="搜索节点…"
                   size="small" class="kg-search" :teleported="false"
                   @change="onSearch">
          <el-option v-for="n in visibleNodes" :key="n.id" :value="n.id" :label="n.label">
            <span class="kg-opt">
              <span class="kg-dot sm" :style="{ background: NODE_META[n.type]?.color }" />
              {{ n.label }}
              <span class="kg-opt-type">{{ typeLabel(n.type) }}</span>
            </span>
          </el-option>
        </el-select>
        <button type="button" class="kg-tool" :class="{ on: legendOpen }" title="图例 / 过滤"
                @click="legendOpen = !legendOpen">
          <el-icon :size="14"><Operation /></el-icon> 图例
        </button>
        <button type="button" class="kg-tool" title="重置缩放与布局" @click="renderChart">
          <el-icon :size="14"><RefreshRight /></el-icon> 重置
        </button>
      </div>
    </div>

    <!-- 统计条：紧贴导航栏下沿（tab 切换数字跟着走） -->
    <div class="kg-statbar" v-if="store.seeded">
      <div v-for="s in statTiles" :key="s.label" class="kg-stat">
        <span class="kg-stat-value">{{ s.value }}</span>
        <span class="kg-stat-label">{{ s.label }}</span>
      </div>
      <span class="kg-statbar-hint">节点大小 = 连接数 · 点击图例行显隐 · 拖拽缩放</span>
    </div>

    <!-- 加载失败（后端不可达等）——与"未初始化"分开，不给跑 seed 的错误指引 -->
    <el-alert v-if="store.error && !store.seeded" type="error" :closable="false"
              :title="`知识图谱加载失败：${store.error}`" />
    <el-empty v-else-if="!store.loading && !store.seeded" description="知识图谱未初始化">
      <template #image><el-icon :size="48"><Connection /></el-icon></template>
      <p class="kg-hint">运行初始化：ecological_env\Scripts\python.exe shared\knowledge_graph\seed_importer.py</p>
    </el-empty>

    <div v-else class="kg-body">
      <aside v-if="legendOpen" class="kg-legend">
        <div class="kg-panel-title">节点类型</div>
        <button v-for="(meta, t) in tabTypes" :key="t" type="button"
                class="kg-type-row" :class="{ off: !store.visibleTypes.includes(String(t)) }"
                @click="store.toggleType(String(t))">
          <span class="kg-swatch" :style="{ background: meta.color }" />
          <span class="kg-type-name">{{ meta.label }}</span>
          <span class="kg-type-count">{{ typeCount(String(t)) }}</span>
        </button>
      </aside>

      <div class="kg-chart-wrap">
        <!-- 推演摘要条：起点 → 波及 N（前3）· 根因候选 M，✕ 退出推演着色；
             案例链路摘要（入口A）与推演互斥共用此容器位 -->
        <div v-if="store.impactResult" class="kg-impact-bar">
          <span>⚡</span>
          <span class="kg-impact-text">
            <b>{{ store.impactResult.node?.label ?? store.impactResult.nodeId }}</b>
            → 波及 {{ store.impactResult.downstream.length }}<template v-if="impactDownLabels">（{{ impactDownLabels }}）</template>
            · 根因候选 {{ store.impactResult.upstream.length }}
          </span>
          <button type="button" class="kg-impact-close" title="退出推演" @click="store.clearImpact">✕</button>
        </div>
        <div v-else-if="store.caseLinkNodes" class="kg-impact-bar kg-case-bar">
          <span>🔗</span>
          <span class="kg-impact-text">
            案例链路：<b>{{ store.caseLinkLabel }}</b>
            （{{ store.caseLinkNodes.size }} 节点：厂→模式→法条）
          </span>
          <button type="button" class="kg-impact-close" title="退出链路高亮" @click="store.clearCaseLink">✕</button>
        </div>
        <el-alert v-if="renderError" type="warning" :closable="false"
                  title="图形渲染失败，已降级为列表视图" />
        <div v-show="!renderError" ref="chartEl" class="kg-chart" />
        <el-table v-if="renderError" class="kg-table" :data="visibleNodes" size="small" height="100%"
                  @row-click="(row: any) => openNode(row.id)">
          <el-table-column prop="id" label="ID" width="280" />
          <el-table-column prop="label" label="名称" />
          <el-table-column prop="type" label="类型" width="120" />
        </el-table>
      </div>

      <div v-if="store.selectedNode || detailLoading" v-loading="detailLoading" class="kg-detail">
        <div class="kg-detail-head">
          <span class="kg-dot" :style="{ background: NODE_META[store.selectedNode?.type ?? '']?.color }" />
          <h3>{{ store.selectedNode?.label }}</h3>
          <span class="kg-detail-type">{{ typeLabel(store.selectedNode?.type ?? '') }}</span>
          <!-- 案例链路入口A：case 节点专属——厂→模式→法条全链蓝色高亮，其余淡出 -->
          <el-button v-if="store.selectedNode?.type === 'case'" text size="small" class="kg-link-btn"
                     @click="toggleCaseLink">
            {{ selectedCaseLinked ? '取消链路' : '🔗 高亮链路' }}
          </el-button>
          <el-button text size="small" @click="store.clearSelection">关闭</el-button>
        </div>
        <el-descriptions v-if="store.selectedNode" :column="1" size="small" border>
          <el-descriptions-item v-for="(v, k) in basicProps" :key="k"
                                :label="String(k)">{{ String(v) }}</el-descriptions-item>
        </el-descriptions>
        <!-- 参数设定区：算子的 params 单独成表（点开节点即见参数是多少——用户需求） -->
        <template v-if="paramRows.length">
          <div class="kg-panel-title kg-nb-title">参数设定</div>
          <el-table :data="paramRows" size="small" :border="true" class="kg-param-table">
            <el-table-column prop="name" label="参数" width="150" />
            <el-table-column prop="value" label="值 / 说明" />
          </el-table>
        </template>
        <div class="kg-panel-title kg-nb-title">关联（一跳）</div>
        <div v-for="(list, ntype) in store.selectedNeighbors" :key="ntype" class="kg-nb-group">
          <div class="kg-nb-type">
            <span class="kg-dot sm" :style="{ background: NODE_META[String(ntype)]?.color }" />
            {{ typeLabel(String(ntype)) }} · {{ list.length }}
          </div>
          <button v-for="n in list" :key="n.id" type="button" class="kg-nb-chip"
                  @click="openNode(n.id)">{{ n.label }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Connection, Operation, RefreshRight } from '@element-plus/icons-vue'
import echarts from '@/lib/echarts'
import {
  useKnowledgeStore, NODE_META, toEChartsSeries, impactNodeStyle,
} from '@/stores/knowledge'
import type { GraphLinkDatum } from '@/stores/knowledge'

const store = useKnowledgeStore()
const chartEl = ref<HTMLDivElement>()
const renderError = ref(false)
let chart: ReturnType<typeof echarts.init> | null = null

// 顶部导航栏状态：图例开合 + 节点搜索（选中即打开详情）
const legendOpen = ref(true)
const searchId = ref('')
function onSearch(id: string) {
  if (id) openNode(id)
  searchId.value = ''
}

// 详情侧栏加载态（store.selectNode 不切换 store.loading，故页面自持）
const detailLoading = ref(false)
async function openNode(id: string) {
  detailLoading.value = true
  try {
    await store.selectNode(id)
  } finally {
    detailLoading.value = false
  }
}

// 案例链路入口A按钮：当前选中的 case 是否正是高亮链路的起点
// （set 里含厂/模式/法条但不含其他 case——case 节点互不为对方链路成员）
const selectedCaseLinked = computed(() =>
  !!store.selectedNode && !!store.caseLinkNodes?.has(store.selectedNode.id))
function toggleCaseLink() {
  const id = store.selectedNode?.id
  if (!id) return
  if (selectedCaseLinked.value) store.clearCaseLink()
  else store.highlightCase(id)
}

// 统计区：大数字 + 灰标签（计数跟当前 tab 走——全图数字与所见不符会造成"68 vs 57"困惑）
const statTiles = computed(() => {
  if (store.activeTab === 'topology') {
    return [
      { value: visibleNodes.value.length, label: '节点' },
      { value: visibleLinksCount.value, label: '关系' },
    ]
  }
  return [
    { value: visibleNodes.value.length, label: '节点' },
    { value: visibleLinksCount.value, label: '关系' },
    { value: store.stats?.node_types?.case ?? 0, label: '案例' },
  ]
})
const visibleLinksCount = computed(() => {
  const vis = new Set(store.visibleTypes)
  const ids = new Set(store.allNodes.filter(n => vis.has(n.type)).map(n => n.id))
  return store.allEdges.filter(e => ids.has(e.src) && ids.has(e.dst)).length
})
const tabTypes = computed(() =>
  Object.fromEntries(Object.entries(NODE_META)
    .filter(([, m]) => m.tab.includes(store.activeTab))))
const visibleNodes = computed(() =>
  store.allNodes.filter(n => store.visibleTypes.includes(n.type)))

function typeLabel(t: string) { return NODE_META[t]?.label ?? t }
function typeCount(t: string) { return store.stats?.node_types?.[t] ?? 0 }

// 详情侧栏：params 抽出单独成表，其余 props 走基础描述表
const basicProps = computed(() => {
  const p = { ...store.selectedNode?.props }
  delete (p as Record<string, unknown>).params
  return p
})
const paramRows = computed(() => {
  const params = store.selectedNode?.props?.params
  if (!params || typeof params !== 'object') return []
  return Object.entries(params as Record<string, unknown>).map(([name, value]) => ({
    name,
    value: typeof value === 'object' ? JSON.stringify(value) : String(value),
  }))
})

function renderChart() {
  if (!chartEl.value || !store.seeded) return
  try {
    if (!chart) chart = echarts.init(chartEl.value)
    const series = toEChartsSeries(store.allNodes, store.allEdges, store.visibleTypes)

    // ── 推演/链路/健康着色叠加（视图层，不进 store 纯映射）──
    // 案例链路（入口A）与推演在 store 层互斥（后者存在时前者必空）——同级分支。
    // fault 红（放大+描边）/ affected 橙 / candidate 紫 覆盖类型色；unrelated 整体退场。
    // service health=down 常态红（#b91c1c 暗红描边区分 fault——无推演时也显示）
    const nodesById = new Map(store.allNodes.map(n => [n.id, n]))
    const linkSet = store.caseLinkNodes // 链内节点集（null=未激活）
    const dataWithImpact: Record<string, unknown>[] = series.data.map(d => {
      const out: Record<string, unknown> = { ...d, itemStyle: { ...d.itemStyle } }
      const itemStyle = out.itemStyle as Record<string, unknown>
      if (linkSet) {
        // 案例链路：链内蓝+深蓝描边，链外淡出
        if (linkSet.has(d.id)) out.itemStyle = { color: '#3b82f6', borderColor: '#1d4ed8', borderWidth: 2 }
        else itemStyle.opacity = 0.15
        return out
      }
      const st = impactNodeStyle(d.id, store.impactResult)
      const raw = nodesById.get(d.id)
      if (st.state === 'fault') {
        out.itemStyle = { color: st.color, borderColor: st.color, borderWidth: 4 }
        out.symbolSize = Math.round(d.symbolSize * 1.3)
      } else if (raw?.type === 'service' && raw.props?.health === 'down') {
        out.itemStyle = { color: '#ef4444', borderColor: '#b91c1c', borderWidth: 2.5 }
      } else if (st.color) {
        itemStyle.color = st.color
      }
      if (st.state === 'unrelated') itemStyle.opacity = 0.15
      return out
    })
    // 边：链路时链内边蓝加粗；推演时影响集（fault∪downstream∪upstream）内部边
    // 橙色加粗；其余场景退到 0.08
    let linksWithImpact: (GraphLinkDatum & { lineStyle?: Record<string, unknown> })[] = series.links
    if (linkSet) {
      linksWithImpact = series.links.map(l =>
        linkSet.has(l.source) && linkSet.has(l.target)
          ? { ...l, lineStyle: { color: '#3b82f6', width: 2, opacity: 0.9 } }
          : { ...l, lineStyle: { opacity: 0.08 } })
    } else if (store.impactResult) {
      const r = store.impactResult
      const inSet = new Set<string>(
        [r.nodeId, ...r.downstream.map(e => e.id), ...r.upstream.map(e => e.id)])
      linksWithImpact = series.links.map(l =>
        inSet.has(l.source) && inSet.has(l.target)
          ? { ...l, lineStyle: { color: '#f97316', width: 2, opacity: 0.9 } }
          : { ...l, lineStyle: { opacity: 0.08 } })
    }
    chart.setOption({
      tooltip: {
        backgroundColor: 'rgba(255,255,255,.96)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: { color: '#1e293b', fontSize: 12 },
        extraCssText: 'box-shadow: 0 4px 16px rgba(15,23,42,.12); border-radius: 8px;',
        // 注意：graph series tooltip 参数无 p.id，节点 id 在 p.data.id（与点击处理一致）
        formatter: (p: any) => p.dataType === 'node'
          ? `<b>${p.name}</b><br/><span style="color:#64748b">${typeLabel(store.allNodes.find(n => n.id === p.data?.id)?.type ?? '')} · ${p.data?.degree ?? 0} 条关联</span>`
          : String(p.value ?? ''),
      },
      series: [{
        type: 'graph',
        layout: 'force',
        force: {
          // 注：echarts 5.6 force.repulsion 只接受 number|number[]（函数形式会让力计算
          // 崩成 NaN、整图不渲染——zrender 连 canvas 都不建）。
          // gravity 拉高把孤立算子收向中心防"沙尘"漂满画布；repulsion 调高防大节点互叠
          repulsion: 300, edgeLength: [55, 130], gravity: 0.35,
          friction: 0.28, layoutAnimation: true,
          initLayout: 'circular',
        },
        roam: true,
        draggable: true,
        scaleLimit: { min: 0.4, max: 4 },
        // 标签：白色描边(halo)让文字在任何底色上可读；宽度截断兜底（tooltip 有全名）
        label: {
          show: true, fontSize: 11, color: '#334155',
          position: 'right', distance: 4,
          width: 130, overflow: 'truncate',
          textBorderColor: '#f6f8fb', textBorderWidth: 2.5,
        },
        labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
        // 边：淡灰细线退后；hover 邻接高亮——结构靠交互读不靠线抢戏
        lineStyle: { color: '#94a3b8', width: 1.2, opacity: 0.6, curveness: 0.12 },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 2.4, opacity: 1, color: '#475569' },
          label: { fontSize: 12, fontWeight: 600 },
          itemStyle: { shadowBlur: 12, shadowColor: 'rgba(15,23,42,.25)' },
        },
        blur: { itemStyle: { opacity: 0.25 }, lineStyle: { opacity: 0.08 } },
        itemStyle: { borderColor: '#fff', borderWidth: 1.5 },
        categories: series.categories,
        data: dataWithImpact,
        links: linksWithImpact,
      }],
    }, { notMerge: true })
    renderError.value = false
    // 力导向收敛后把图心居中（防重心偏移/顶边裁切）
    if (series.data.length) centerAfterLayout()
  } catch (e) {
    console.error('知识图谱渲染失败', e)
    renderError.value = true // 降级表格
  }
}

/** 力导向收敛后把图心移到画布中心（多次渲染复用同一计时器） */
let centerTimer: ReturnType<typeof setTimeout> | null = null
function centerAfterLayout() {
  if (centerTimer) clearTimeout(centerTimer)
  centerTimer = setTimeout(() => {
    if (!chart || !chartEl.value) return
    chart.setOption({ series: [{ center: ['50%', '50%'] }] })
    centerTimer = null
  }, 700)
}

function onNodeClick(params: any) {
  if (params.dataType !== 'node' || !params.data?.id) return
  // 推演模式分流：点节点=跑影响推演（不开详情侧栏），普通模式=打开详情
  if (store.impactMode) store.runImpact(params.data.id)
  else openNode(params.data.id)
}
function onResize() { chart?.resize() }

// 推演摘要条：波及名单前 3（多则省略号）
const impactDownLabels = computed(() => {
  const ds = store.impactResult?.downstream ?? []
  const names = ds.slice(0, 3).map(e => e.label || e.id).join('、')
  return ds.length > 3 ? `${names}…` : names
})

// 服务健康 60s 慢轮询句柄（后端探测自带 10s 缓存，页面分钟级足够）
let healthTimer: ReturnType<typeof setInterval> | null = null
const route = useRoute()

onMounted(async () => {
  await store.loadGraph()
  await nextTick()
  renderChart()
  chart?.on('click', onNodeClick)
  window.addEventListener('resize', onResize)
  healthTimer = setInterval(() => { store.refreshHealth().catch(() => {}) }, 60_000)
  // focus query：?focus=<node_id> 直开详情侧栏（事件中心等外链深入口）
  const focus = typeof route.query.focus === 'string' ? route.query.focus : ''
  if (focus) openNode(focus)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (healthTimer) clearInterval(healthTimer)
  if (centerTimer) clearTimeout(centerTimer)
  chart?.dispose()
  chart = null
})

// tab/图例/数据/推演结果/案例链路变化 → 重渲染（visibleTypes 是 computed 新数组、allNodes 整体
// 替换，引用比较即触发，无需 deep；impactResult/caseLinkNodes 置换触发着色进/退场；nextTick 兜底，
// 项目历史坑：echarts.init 必须在 DOM 就绪后）
watch([() => store.visibleTypes, () => store.allNodes, () => store.impactResult, () => store.caseLinkNodes],
  () => nextTick(renderChart))

// 详情侧栏出现/消失使图区宽度变化 → resize，否则 canvas 按旧宽度溢出、盖住侧栏拦截点击
watch(() => store.selectedNode, () => nextTick(() => chart?.resize()))
</script>

<style scoped>
.kg-page { padding: 16px 20px; height: 100%; display: flex; flex-direction: column; gap: 12px; }

/* ── 页面级顶部导航栏 ── */
.kg-navbar {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: var(--card-radius, 12px);
  box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,.06));
  padding: 12px 16px;
}
.kg-navbar-left { display: flex; align-items: center; gap: 18px; min-width: 0; }
.kg-navbar-title { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.kg-navbar-name { font-size: 17px; font-weight: 700; color: var(--text-primary, #1e293b); line-height: 1.2; }
.kg-navbar-sub { font-size: 12px; color: var(--text-muted, #94a3b8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kg-navbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.kg-search { width: 200px; }
.kg-tool {
  display: flex; align-items: center; gap: 5px;
  padding: 7px 12px; border: 1px solid var(--el-border-color-light, #e4e7ed); border-radius: 8px;
  background: #fff; color: var(--text-secondary, #64748b);
  font-size: 12px; cursor: pointer; font-family: inherit; transition: all .15s;
}
.kg-tool:hover, .kg-tool.on { color: var(--primary, #6366f1); border-color: var(--primary, #6366f1); background: rgba(99,102,241,.05); }
.kg-opt { display: flex; align-items: center; gap: 6px; }
.kg-opt-type { margin-left: auto; color: var(--text-muted, #94a3b8); font-size: 12px; }

/* ── 统计条（导航栏下沿） ── */
.kg-statbar { display: flex; align-items: center; gap: 0; padding: 0 4px; }
.kg-stat { display: flex; flex-direction: column; gap: 1px; padding-right: 18px; }
.kg-stat + .kg-stat { padding-left: 18px; border-left: 1px solid var(--el-border-color-lighter, #f1f5f9); }
.kg-stat-value { font-size: 22px; font-weight: 700; line-height: 1.1; color: var(--text-primary, #1e293b); font-variant-numeric: tabular-nums; }
.kg-stat-label { font-size: 12px; color: var(--text-muted, #94a3b8); letter-spacing: .04em; }
.kg-statbar-hint { margin-left: auto; font-size: 12px; color: var(--text-muted, #94a3b8); }

.kg-body { flex: 1; display: flex; gap: 14px; min-height: 0; }

/* 图例：类型行（色点+名+计数），非表单观感；点击整行切换显隐 */
.kg-legend {
  width: 168px; flex-shrink: 0; padding: 14px 12px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: var(--card-radius, 12px);
  box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,.06));
  display: flex; flex-direction: column; gap: 2px;
}
.kg-panel-title { font-size: 11px; font-weight: 600; color: var(--text-muted, #94a3b8); letter-spacing: .08em; margin-bottom: 8px; }
.kg-type-row {
  display: flex; align-items: center; gap: 8px; width: 100%;
  padding: 6px 8px; border: 0; background: transparent; border-radius: 8px;
  cursor: pointer; text-align: left; font: inherit; color: var(--text-primary, #1e293b);
  transition: background .15s;
}
.kg-type-row:hover { background: var(--sidebar-hover, #f1f5f9); }
.kg-type-row.off { opacity: .38; }
.kg-type-row.off .kg-type-name { text-decoration: line-through; text-decoration-color: var(--text-muted); }
.kg-swatch { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.kg-type-name { font-size: 13px; flex: 1; }
.kg-type-count { font-size: 12px; color: var(--text-muted, #94a3b8); font-variant-numeric: tabular-nums; }

/* 图区：整卡承托（与图例/详情同质感），给图完整画布 */
.kg-chart-wrap {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  background: linear-gradient(180deg, #fbfcfe 0%, #f6f8fb 100%);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: var(--card-radius, 12px);
  box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,.06));
  overflow: hidden; position: relative;
}
.kg-chart { flex: 1; min-height: 0; }
.kg-table :deep(.el-table__row) { cursor: pointer; }

/* ── 影响推演 ── */
.kg-bolt { font-size: 13px; line-height: 1; } /* ⚡ 字符随按钮色走，激活态与文字同变紫 */
/* 摘要条：图区顶部居中浮层（琥珀底=推演语境，与故障红/波及橙区分） */
.kg-impact-bar {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  z-index: 10; display: flex; align-items: center; gap: 8px;
  max-width: calc(100% - 32px);
  padding: 7px 8px 7px 14px;
  background: rgba(255,251,235,.97);
  border: 1px solid #f59e0b; border-radius: 10px;
  box-shadow: 0 4px 16px rgba(180,83,9,.15);
  font-size: 12px; color: #92400e;
}
.kg-impact-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.kg-impact-text b { color: #b45309; }
.kg-impact-close {
  border: 0; background: transparent; cursor: pointer; flex-shrink: 0;
  color: #b45309; font-size: 13px; line-height: 1; padding: 3px 6px; border-radius: 6px;
}
.kg-impact-close:hover { background: rgba(180,83,9,.1); }
/* 案例链路摘要条（蓝=链路语境，与推演琥珀底区分；结构复用 .kg-impact-bar） */
.kg-case-bar {
  background: rgba(239,246,255,.97); border-color: #3b82f6;
  box-shadow: 0 4px 16px rgba(30,64,175,.15); color: #1e40af;
}
.kg-case-bar .kg-impact-text b { color: #1d4ed8; }
.kg-case-bar .kg-impact-close { color: #1d4ed8; }
.kg-case-bar .kg-impact-close:hover { background: rgba(29,78,216,.1); }
.kg-link-btn { color: #1d4ed8; }
.kg-link-btn:hover { color: #1d4ed8; background: rgba(29,78,216,.06); }

/* 详情侧栏 */
.kg-detail {
  width: 296px; flex-shrink: 0; padding: 16px 14px; overflow-y: auto;
  background: var(--card-bg, #fff);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: var(--card-radius, 12px);
  box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,.06));
}
.kg-detail-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.kg-detail-head h3 { margin: 0; font-size: 15px; font-weight: 600; flex: 1; color: var(--text-primary, #1e293b); }
.kg-detail-type { font-size: 12px; color: var(--text-muted, #94a3b8); flex-shrink: 0; }
.kg-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.kg-dot.sm { width: 7px; height: 7px; }
.kg-nb-title { margin-top: 14px; }
.kg-param-table { margin-top: 4px; }
.kg-nb-group { margin-bottom: 10px; }
.kg-nb-type { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary, #64748b); margin-bottom: 6px; }
.kg-nb-chip {
  display: inline-block; margin: 0 4px 4px 0; padding: 3px 10px;
  border: 1px solid var(--el-border-color-light, #e4e7ed); border-radius: 999px;
  background: #fff; font-size: 12px; color: var(--text-primary, #1e293b);
  cursor: pointer; transition: all .15s; font-family: inherit;
}
.kg-nb-chip:hover { border-color: var(--primary, #6366f1); color: var(--primary, #6366f1); background: rgba(99,102,241,.04); }
.kg-hint { color: var(--text-secondary, #64748b); font-size: 12px; }
</style>
