<template>
  <div class="evc">
    <div class="head">
      <div class="ttl">事件中心</div>
      <div class="filters">
        <el-select v-model="severity" placeholder="严重度" clearable size="small" style="width:120px" @change="load">
          <el-option v-for="s in ['low','medium','high']" :key="s" :label="sevLabel(s)" :value="s" />
        </el-select>
        <el-select v-model="status" placeholder="状态" clearable size="small" style="width:120px" @change="load">
          <el-option v-for="s in ['pending','processing','resolved','ignored']" :key="s" :label="statusLabel(s)" :value="s" />
        </el-select>
      </div>
    </div>

    <el-table :data="events" v-loading="loading" stripe style="width: 100%" @row-click="openDetail">
      <el-table-column label="时间" width="170">
        <template #default="{ row }"><span class="ts">{{ fmt(row.timestamp) }}</span></template>
      </el-table-column>
      <el-table-column label="类型" min-width="130">
        <template #default="{ row }">{{ (row.violationTypes || []).join('、') || '—' }}</template>
      </el-table-column>
      <el-table-column label="厂区" width="120" prop="plantId" />
      <el-table-column label="严重度" width="100">
        <template #default="{ row }"><el-tag size="small" :type="sevType(row.severity)" effect="dark">{{ sevLabel(row.severity) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }"><el-tag size="small" :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag></template>
      </el-table-column>
    </el-table>
    <div v-if="!loading && !events.length" class="empty">无匹配事件</div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`事件详情 · ${current?.id || ''}`" direction="rtl" size="560px">
      <template v-if="current">
        <div class="d-meta">
          <div><span class="k">类型</span>{{ (current.violationTypes || []).join('、') || '—' }}</div>
          <div><span class="k">厂区</span>{{ current.plantId }}</div>
          <div><span class="k">时间</span>{{ fmt(current.timestamp) }}</div>
          <div><span class="k">严重度</span>
            <el-tag size="small" :type="sevType(current.severity)" effect="dark">{{ sevLabel(current.severity) }}</el-tag>
          </div>
        </div>

        <!-- 状态流转 -->
        <div class="d-status">
          <span class="k">处置状态</span>
          <el-select v-model="current.status" size="small" style="width:140px" @change="saveStatus">
            <el-option v-for="s in ['pending','processing','resolved','ignored']" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </div>

        <!-- 研判行动 -->
        <div class="d-sec">
          <div class="d-ttl">研判行动</div>
          <div class="li">▸ <b>{{ current.action || '—' }}</b>
            <span v-if="current.confidence != null" class="muted">置信度 {{ (current.confidence * 100).toFixed(1) }}%</span>
          </div>
        </div>

        <!-- 指标异常点 -->
        <div class="d-sec" v-if="splitEvidence(current.evidence).anomalies.length">
          <div class="d-ttl">指标异常点（{{ splitEvidence(current.evidence).anomalies.length }}）</div>
          <el-table :data="splitEvidence(current.evidence).anomalies" size="small" style="width: 100%">
            <el-table-column label="指标" prop="indicator" width="70" />
            <el-table-column label="时间" width="140">
              <template #default="{ row }"><span class="ts">{{ row.timestamp || '—' }}</span></template>
            </el-table-column>
            <el-table-column label="实测值" width="90">
              <template #default="{ row }">{{ row.value != null ? row.value : '—' }}</template>
            </el-table-column>
            <el-table-column label="期望区间">
              <template #default="{ row }">{{ row.expected_range ? row.expected_range.join(' ~ ') : '—' }}</template>
            </el-table-column>
            <el-table-column label="得分" width="80">
              <template #default="{ row }">{{ row.score != null ? row.score.toFixed(2) : '—' }}</template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 专家模式命中 -->
        <div class="d-sec" v-if="splitEvidence(current.evidence).patterns.length">
          <div class="d-ttl">专家模式命中（{{ splitEvidence(current.evidence).patterns.length }}）</div>
          <div v-for="p in splitEvidence(current.evidence).patterns" :key="p.pattern_key || p.pattern" class="li">
            ▸ <b>{{ p.pattern }}</b>
            <span class="muted">匹配 {{ p.match_score != null ? (p.match_score * 100).toFixed(0) + '%' : '—' }}</span>
            <span class="muted">置信 {{ p.confidence != null ? (p.confidence * 100).toFixed(0) + '%' : '—' }}</span>
            <el-tag size="small" :type="suspicionType(p.suspicion_level)" effect="plain">{{ p.suspicion_level || '—' }}</el-tag>
          </div>
        </div>

        <!-- 工单摘要 -->
        <div class="d-sec" v-if="current.workOrder">
          <div class="d-ttl">处置工单</div>
          <div class="li">▸ <b>{{ String(current.workOrder.id ?? '—') }}</b>
            <span class="muted">{{ fmt(String(current.workOrder.generated_at ?? '')) }}</span>
          </div>
          <div class="li" v-for="a in recommendedActions(current.workOrder)" :key="a">· {{ a }}</div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { eventsService } from '@/api/modules/events'
import { splitEvidence } from '@/views/eventEvidence'
import type { AlertEvent } from '@/api/types/api.types'

const events = ref<AlertEvent[]>([])
const loading = ref(false)
const severity = ref('')
const status = ref('')

const drawerVisible = ref(false)
const current = ref<AlertEvent | null>(null)

async function load() {
  loading.value = true
  try {
    const r = await eventsService.list({ severity: severity.value || undefined, status: status.value || undefined })
    events.value = r.data
  } catch { events.value = [] }
  finally { loading.value = false }
}
function openDetail(row: AlertEvent) {
  current.value = row
  drawerVisible.value = true
}
async function saveStatus(s: string) {
  if (!current.value) return
  try {
    await eventsService.updateStatus(current.value.id, s)
    ElMessage.success('状态已更新')
  } catch { /* 拦截器已弹错 */ }
}

function fmt(t: string) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }
// 工单推荐行动切前三条
function recommendedActions(wo: Record<string, unknown> | null | undefined): string[] {
  const a = wo?.recommended_actions
  return Array.isArray(a) ? (a as unknown[]).map(String).slice(0, 3) : []
}
function suspicionType(s: string): 'info' | 'warning' | 'danger' {
  return s === 'critical' || s === 'high' ? 'danger' : s === 'medium' ? 'warning' : 'info'
}
const SEV_LBL: Record<string, string> = { low: '低', medium: '中', high: '高' }
const STATUS_LBL: Record<string, string> = { pending: '待处理', processing: '处理中', resolved: '已解决', ignored: '已忽略' }
function sevLabel(s: string) { return SEV_LBL[s] || s }
function statusLabel(s: string) { return STATUS_LBL[s] || s }
function sevType(s: string): 'info' | 'warning' | 'danger' { return s === 'high' ? 'danger' : s === 'medium' ? 'warning' : 'info' }
function statusType(s: string): 'info' | 'warning' | 'success' | 'danger' { return s === 'resolved' ? 'success' : s === 'pending' ? 'danger' : 'info' }

onMounted(load)
</script>

<style scoped>
.evc { display: flex; flex-direction: column; gap: 14px }
.head { display: flex; justify-content: space-between; align-items: center }
.ttl { font-size: 16px; font-weight: 700 }
.filters { display: flex; gap: 8px }
.ts { font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums }
.empty { color: var(--text-muted); font-size: 13px; padding: 24px; text-align: center }
.d-meta { display: flex; flex-direction: column; gap: 7px; background: var(--surface-1); border: 1px solid var(--brd);
  border-radius: 10px; padding: 12px 14px; margin-bottom: 14px }
.d-meta .k { display: inline-block; width: 60px; color: var(--text-muted); font-size: 11px }
.d-status { display: flex; align-items: center; gap: 12px; margin-bottom: 16px }
.d-status .k { color: var(--text-muted); font-size: 12px }
.d-sec { display: flex; flex-direction: column; gap: 4px }
.d-ttl { font-size: 12px; font-weight: 700; color: var(--text-secondary); margin: 12px 0 4px; letter-spacing: .5px }
.d-ttl:first-child { margin-top: 0 }
.li { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 8px; margin-bottom: 3px }
.li b { color: var(--text-primary) }
.muted { color: var(--text-muted); font-size: 11px }
</style>
