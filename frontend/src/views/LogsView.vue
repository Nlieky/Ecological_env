<template>
  <div class="logs">
    <div class="head">
      <div class="ttl">系统日志</div>
      <div class="bar">
        <el-radio-group v-model="logType" @change="onTypeChange">
          <el-radio-button v-for="t in TYPES" :key="t.v" :label="t.v">{{ t.t }}</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading" stripe style="width: 100%">
      <el-table-column label="时间" width="170">
        <template #default="{ row }"><span class="ts">{{ row.timestamp || '—' }}</span></template>
      </el-table-column>
      <el-table-column label="模块" width="110" prop="module" />
      <el-table-column label="耗时" width="100">
        <template #default="{ row }">{{ row.latency_ms != null ? Math.round(row.latency_ms) + ' ms' : '—' }}</template>
      </el-table-column>
      <el-table-column label="内容" min-width="320">
        <template #default="{ row }"><span class="content" :title="row.content">{{ row.content || '—' }}</span></template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <span class="total">共 {{ total }} 条</span>
      <el-pagination background layout="prev, pager, next" :total="total" :page-size="PAGE" :current-page="page"
        @current-change="onPage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { logsService } from '@/api/modules/logs'
import type { LogEntryV1, LogType } from '@/api/types/api.types'

const TYPES: { v: LogType; t: string }[] = [
  { v: 'api', t: 'API' },
  { v: 'master', t: '主智能体' },
  { v: 'subagent', t: '子智能体' },
  { v: 'operator', t: '算子' },
  { v: 'llm', t: 'LLM' },
  { v: 'error', t: '错误' },
]
const PAGE = 20

const logType = ref<LogType>('api')
const rows = ref<LogEntryV1[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const r = await logsService.list({ log_type: logType.value, page: page.value, page_size: PAGE })
    rows.value = r.data
    total.value = r.total
  } catch { rows.value = []; total.value = 0 }
  finally { loading.value = false }
}
function onTypeChange() { page.value = 1; void load() }
function onPage(p: number) { page.value = p; void load() }

onMounted(load)
</script>

<style scoped>
.logs { display: flex; flex-direction: column; gap: 14px }
.head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px }
.ttl { font-size: 16px; font-weight: 700 }
.ts { font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums }
.content { font-size: 12px; color: var(--text-muted); font-family: ui-monospace, monospace;
  display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom }
.pager { display: flex; justify-content: space-between; align-items: center; margin-top: 4px }
.total { font-size: 12px; color: var(--text-muted) }
</style>
