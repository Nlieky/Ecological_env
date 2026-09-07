<template>
  <div class="kg-page">
    <div class="kg-header">
      <div class="kg-title">
        <h2>知识图谱</h2>
        <span v-if="store.stats" class="kg-badges">
          <el-tag size="small">{{ store.stats.nodes }} 节点</el-tag>
          <el-tag size="small" type="warning">{{ store.stats.edges }} 关系</el-tag>
          <el-tag size="small" type="danger">{{ caseCount }} 案例</el-tag>
        </span>
      </div>
      <el-radio-group :model-value="store.activeTab" size="small" @update:model-value="store.setTab">
        <el-radio-button value="domain">领域知识</el-radio-button>
        <el-radio-button value="topology">服务拓扑</el-radio-button>
      </el-radio-group>
    </div>

    <el-empty v-if="!store.loading && !store.seeded" description="知识图谱未初始化">
      <template #image><el-icon :size="48"><Connection /></el-icon></template>
      <p class="kg-hint">运行初始化：ecological_env\Scripts\python.exe shared\knowledge_graph\seed_importer.py</p>
    </el-empty>

    <div v-else class="kg-body">
      <div class="kg-legend">
        <div class="label">图例 / 过滤</div>
        <el-checkbox-group :model-value="checkedTypes" @update:model-value="onLegendChange">
          <el-checkbox v-for="(meta, t) in tabTypes" :key="t" :value="t">
            <span :style="{ color: meta.color }">●</span> {{ meta.label }}
            <span class="kg-count">{{ typeCount(String(t)) }}</span>
          </el-checkbox>
        </el-checkbox-group>
      </div>

      <div class="kg-chart-wrap">
        <el-alert v-if="renderError" type="warning" :closable="false"
                  title="图形渲染失败，已降级为列表视图" />
        <div v-show="!renderError" ref="chartEl" class="kg-chart" />
        <el-table v-if="renderError" :data="visibleNodes" size="small" height="100%">
          <el-table-column prop="id" label="ID" width="280" />
          <el-table-column prop="label" label="名称" />
          <el-table-column prop="type" label="类型" width="120" />
        </el-table>
      </div>

      <div v-if="store.selectedNode" class="kg-detail">
        <div class="kg-detail-head">
          <h3>{{ store.selectedNode.label }}</h3>
          <el-tag size="small">{{ typeLabel(store.selectedNode.type) }}</el-tag>
          <el-button text size="small" @click="store.clearSelection">关闭</el-button>
        </div>
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item v-for="(v, k) in store.selectedNode.props" :key="k"
                                :label="String(k)">{{ String(v) }}</el-descriptions-item>
        </el-descriptions>
        <div class="label kg-nb-title">关联（一跳）</div>
        <div v-for="(list, ntype) in store.selectedNeighbors" :key="ntype" class="kg-nb-group">
          <div class="label">{{ typeLabel(String(ntype)) }}（{{ list.length }}）</div>
          <el-tag v-for="n in list" :key="n.id" class="kg-nb-tag"
                  @click="store.selectNode(n.id)">{{ n.label }}</el-tag>
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

const caseCount = computed(() => store.stats?.node_types?.case ?? 0)
const tabTypes = computed(() =>
  Object.fromEntries(Object.entries(NODE_META)
    .filter(([, m]) => m.tab === store.activeTab)))
const visibleNodes = computed(() =>
  store.allNodes.filter(n => store.visibleTypes.includes(n.type)))

/** 勾选态=不在 hiddenTypes 里（hiddenTypes 空=全显） */
const checkedTypes = computed(() =>
  store.visibleTypes) // 当前可见即勾选
function onLegendChange(vals: string[]) {
  // 把 tab 内全部类型里不在 vals 的加进 hiddenTypes；在的移出
  const all = Object.keys(NODE_META).filter(k => NODE_META[k].tab === store.activeTab)
  for (const t of all) {
    const shouldHide = !vals.includes(t)
    const isHidden = store.hiddenTypes.includes(t)
    if (shouldHide !== isHidden) store.toggleType(t)
  }
}

function typeLabel(t: string) { return NODE_META[t]?.label ?? t }
function typeCount(t: string) { return store.stats?.node_types?.[t] ?? 0 }

function renderChart() {
  if (!chartEl.value || !store.seeded) return
  try {
    if (!chart) chart = echarts.init(chartEl.value)
    const series = toEChartsSeries(store.allNodes, store.allEdges, store.visibleTypes)
    chart.setOption({
      tooltip: {
        formatter: (p: any) => p.dataType === 'node'
          ? `${p.name}（${typeLabel(store.allNodes.find(n => n.id === p.id)?.type ?? '')}）`
          : String(p.value ?? ''),
      },
      legend: { data: series.categories.map(c => c.name), bottom: 0 },
      series: [{
        type: 'graph',
        layout: 'force',
        force: { repulsion: 120, edgeLength: [40, 90], gravity: 0.08 },
        roam: true,
        draggable: true,
        label: { show: true, fontSize: 11 },
        emphasis: { focus: 'adjacency' },
        categories: series.categories,
        data: series.data,
        links: series.links,
      }],
    }, { notMerge: true })
    renderError.value = false
  } catch {
    renderError.value = true // 降级表格
  }
}

function onNodeClick(params: any) {
  if (params.dataType === 'node' && params.data?.id) store.selectNode(params.data.id)
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
  chart?.dispose()
  chart = null
})

// tab/图例/数据变化 → 重渲染（nextTick 兜底，项目历史坑：echarts.init 必须在 DOM 就绪后）
watch([() => store.visibleTypes, () => store.allNodes],
  () => nextTick(renderChart), { deep: true })

// 详情侧栏出现/消失使图区宽度变化 → resize，否则 canvas 按旧宽度溢出、盖住侧栏拦截点击
watch(() => store.selectedNode, () => nextTick(() => chart?.resize()))
</script>

<style scoped>
.kg-page { padding: 16px; height: 100%; display: flex; flex-direction: column; }
.kg-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.kg-title { display: flex; align-items: center; gap: 12px; }
.kg-title h2 { margin: 0; font-size: 18px; }
.kg-badges { display: flex; gap: 6px; }
.kg-body { flex: 1; display: flex; gap: 12px; min-height: 0; }
.kg-legend { width: 180px; flex-shrink: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; overflow-y: auto; }
.kg-legend .el-checkbox { display: flex; margin-right: 0; }
.kg-count { color: var(--el-text-color-secondary); font-size: 12px; margin-left: 4px; }
.kg-chart-wrap { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.kg-chart { flex: 1; min-height: 0; }
.kg-detail { width: 300px; flex-shrink: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; overflow-y: auto; }
.kg-detail-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.kg-detail-head h3 { margin: 0; font-size: 15px; flex: 1; }
.kg-nb-title { margin-top: 12px; }
.kg-nb-group { margin-bottom: 8px; }
.kg-nb-tag { cursor: pointer; margin: 2px; }
.kg-hint { color: var(--el-text-color-secondary); font-size: 12px; }
</style>
