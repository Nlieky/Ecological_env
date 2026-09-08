<template>
  <div class="kg-page">
    <div class="kg-header">
      <div class="kg-stats">
        <div v-for="s in statTiles" :key="s.label" class="kg-stat">
          <span class="kg-stat-value">{{ s.value }}</span>
          <span class="kg-stat-label">{{ s.label }}</span>
        </div>
      </div>
      <el-radio-group :model-value="store.activeTab" size="small" @update:model-value="store.setTab">
        <el-radio-button value="domain">领域知识</el-radio-button>
        <el-radio-button value="topology">服务拓扑</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 加载失败（后端不可达等）——与"未初始化"分开，不给跑 seed 的错误指引 -->
    <el-alert v-if="store.error && !store.seeded" type="error" :closable="false"
              :title="`知识图谱加载失败：${store.error}`" />
    <el-empty v-else-if="!store.loading && !store.seeded" description="知识图谱未初始化">
      <template #image><el-icon :size="48"><Connection /></el-icon></template>
      <p class="kg-hint">运行初始化：ecological_env\Scripts\python.exe shared\knowledge_graph\seed_importer.py</p>
    </el-empty>

    <div v-else class="kg-body">
      <aside class="kg-legend">
        <div class="kg-panel-title">节点类型</div>
        <button v-for="(meta, t) in tabTypes" :key="t" type="button"
                class="kg-type-row" :class="{ off: !store.visibleTypes.includes(String(t)) }"
                @click="store.toggleType(String(t))">
          <span class="kg-swatch" :style="{ background: meta.color }" />
          <span class="kg-type-name">{{ meta.label }}</span>
          <span class="kg-type-count">{{ typeCount(String(t)) }}</span>
        </button>
        <div class="kg-legend-foot">节点大小 = 连接数<br/>点击行显隐 · 拖拽缩放</div>
      </aside>

      <div class="kg-chart-wrap">
        <el-alert v-if="renderError" type="warning" :closable="false"
                  title="图形渲染失败，已降级为列表视图" />
        <button v-if="!renderError" type="button" class="kg-reset" title="重置缩放与布局"
                @click="renderChart">⤢ 重置视图</button>
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
          <el-button text size="small" @click="store.clearSelection">关闭</el-button>
        </div>
        <el-descriptions v-if="store.selectedNode" :column="1" size="small" border>
          <el-descriptions-item v-for="(v, k) in store.selectedNode.props" :key="k"
                                :label="String(k)">{{ String(v) }}</el-descriptions-item>
        </el-descriptions>
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
import { Connection } from '@element-plus/icons-vue'
import echarts from '@/lib/echarts'
import { useKnowledgeStore, NODE_META, toEChartsSeries } from '@/stores/knowledge'

const store = useKnowledgeStore()
const chartEl = ref<HTMLDivElement>()
const renderError = ref(false)
let chart: ReturnType<typeof echarts.init> | null = null

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

function renderChart() {
  if (!chartEl.value || !store.seeded) return
  try {
    if (!chart) chart = echarts.init(chartEl.value)
    const series = toEChartsSeries(store.allNodes, store.allEdges, store.visibleTypes)
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
        data: series.data,
        links: series.links,
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
  if (params.dataType === 'node' && params.data?.id) openNode(params.data.id)
}
function onResize() { chart?.resize() }

onMounted(async () => {
  await store.loadGraph()
  await nextTick()
  renderChart()
  chart?.on('click', onNodeClick)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (centerTimer) clearTimeout(centerTimer)
  chart?.dispose()
  chart = null
})

// tab/图例/数据变化 → 重渲染（visibleTypes 是 computed 新数组、allNodes 整体替换，
// 引用比较即触发，无需 deep；nextTick 兜底，项目历史坑：echarts.init 必须在 DOM 就绪后）
watch([() => store.visibleTypes, () => store.allNodes],
  () => nextTick(renderChart))

// 详情侧栏出现/消失使图区宽度变化 → resize，否则 canvas 按旧宽度溢出、盖住侧栏拦截点击
watch(() => store.selectedNode, () => nextTick(() => chart?.resize()))
</script>

<style scoped>
.kg-page { padding: 20px 24px; height: 100%; display: flex; flex-direction: column; gap: 14px; }
.kg-header { display: flex; justify-content: space-between; align-items: center; }

/* 统计区：大数字+灰标签+竖分隔（替换彩色 pill 徽标） */
.kg-stats { display: flex; align-items: stretch; }
.kg-stat { display: flex; flex-direction: column; gap: 2px; padding-right: 20px; }
.kg-stat + .kg-stat { padding-left: 20px; border-left: 1px solid var(--el-border-color-lighter, #f1f5f9); }
.kg-stat-value { font-size: 24px; font-weight: 700; line-height: 1.1; color: var(--text-primary, #1e293b); font-variant-numeric: tabular-nums; }
.kg-stat-label { font-size: 12px; color: var(--text-muted, #94a3b8); letter-spacing: .04em; }
.kg-stat + .kg-stat .kg-stat-value::after { content: ''; }

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
.kg-legend-foot { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--el-border-color-lighter, #f1f5f9); font-size: 11px; color: var(--text-muted, #94a3b8); line-height: 1.5; }

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
.kg-reset {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  padding: 5px 12px; border: 1px solid var(--el-border-color-light, #e4e7ed); border-radius: 8px;
  background: rgba(255,255,255,.92); color: var(--text-secondary, #64748b);
  font-size: 12px; cursor: pointer; font-family: inherit;
  box-shadow: 0 1px 3px rgba(15,23,42,.08); transition: all .15s;
}
.kg-reset:hover { color: var(--primary, #6366f1); border-color: var(--primary, #6366f1); }
.kg-table :deep(.el-table__row) { cursor: pointer; }

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
