<template>
  <div class="alc">
    <div class="head">
      <div class="ttl">告警中心</div>
      <el-button size="small" @click="load" :loading="loading">刷新</el-button>
    </div>

    <!-- 统计卡片(待处理告警聚合)-->
    <div class="stats">
      <div class="card danger"><div class="num">{{ pending.length }}</div><div class="lbl">待处理</div></div>
      <div class="card danger"><div class="num">{{ cnt('high') }}</div><div class="lbl">高危</div></div>
      <div class="card warn"><div class="num">{{ cnt('medium') }}</div><div class="lbl">中级</div></div>
      <div class="card info"><div class="num">{{ cnt('low') }}</div><div class="lbl">低级</div></div>
    </div>

    <!-- 待处理告警列表 + 行内快捷处置 -->
    <el-table :data="pending" v-loading="loading" stripe @row-click="goEvents">
      <el-table-column label="时间" width="170">
        <template #default="{ row }"><span class="ts">{{ fmt(row.timestamp) }}</span></template>
      </el-table-column>
      <el-table-column label="类型" min-width="130" prop="type" />
      <el-table-column label="厂区" width="120" prop="plantId" />
      <el-table-column label="严重度" width="90">
        <template #default="{ row }"><el-tag size="small" :type="sevType(row.severity)" effect="dark">{{ sevLabel(row.severity) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="快捷处置" width="190">
        <template #default="{ row }">
          <el-button size="small" type="success" @click.stop="quick(row, 'resolved')">已处置</el-button>
          <el-button size="small" @click.stop="quick(row, 'ignored')">忽略</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="!loading && !pending.length" class="empty">
      🎉 暂无待处理告警 · <router-link to="/events">查看事件中心全部</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { eventsService } from '@/api/modules/events'
import type { AlertEvent } from '@/api/types/api.types'

const router = useRouter()
const all = ref<AlertEvent[]>([])
const loading = ref(false)

// 待处理 = pending / processing(未 resolved/ignored)
const pending = computed(() => all.value.filter(e => e.status === 'pending' || e.status === 'processing'))
const cnt = (sev: string) => pending.value.filter(e => e.severity === sev).length

async function load() {
  loading.value = true
  try {
    const r = await eventsService.list()
    all.value = (r?.data as AlertEvent[]) || []
  } catch { all.value = [] }
  finally { loading.value = false }
}

async function quick(row: AlertEvent, status: string) {
  try {
    await eventsService.updateStatus(row.id, status)
    ElMessage.success(status === 'resolved' ? '已标记处置' : '已忽略')
    await load()
  } catch { /* 拦截器已弹错 */ }
}

function goEvents() {
  // 告警中心聚焦待办快捷处置;详情/证据走事件中心
  router.push('/events')
}

function fmt(t: string) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }
const SEV_LBL: Record<string, string> = { low: '低', medium: '中', high: '高' }
function sevLabel(s: string) { return SEV_LBL[s] || s }
function sevType(s: string): 'info' | 'warning' | 'danger' { return s === 'high' ? 'danger' : s === 'medium' ? 'warning' : 'info' }

onMounted(load)
</script>

<style scoped>
.alc { display: flex; flex-direction: column; gap: 14px }
.head { display: flex; justify-content: space-between; align-items: center }
.ttl { font-size: 16px; font-weight: 700 }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px }
.card { background: var(--surface-1); border: 1px solid var(--brd); border-radius: 10px; padding: 14px; text-align: center; border-left: 4px solid var(--el-color-info, #909399) }
.card.danger { border-left-color: var(--el-color-danger, #f56c6c) }
.card.warn { border-left-color: var(--el-color-warning, #e6a23c) }
.card.info { border-left-color: var(--el-color-info, #909399) }
.num { font-size: 26px; font-weight: 700 }
.lbl { font-size: 12px; color: var(--text-muted); margin-top: 2px }
.ts { font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums }
.empty { color: var(--text-muted); font-size: 13px; padding: 24px; text-align: center }
</style>
