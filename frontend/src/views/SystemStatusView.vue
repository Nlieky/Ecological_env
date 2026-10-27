<template>
  <div class="sys">
    <div class="hd">
      <span class="sub">生成于 {{ shanghaiTime(status?.generated_at) }} · Asia/Shanghai · {{ polling ? `${POLL_MS / 1000}s 自动刷新` : '已暂停' }}</span>
      <button class="pause" :class="{ on: !polling }" @click="togglePolling">{{ polling ? '⏸ 暂停' : '▶ 恢复' }}</button>
    </div>

    <PageState :state="viewState" :preserve-content="!!status" :message="error ? (status ? '刷新失败，保留上次加载的数据。' : '系统态势加载失败，请重试。') : undefined" @retry="load">
    <p v-if="error" role="alert">{{ error }}</p>
    <template v-if="status">
      <!-- 服务健康 -->
      <div class="sec-ttl">服务状态</div>
      <div class="svc-grid">
        <div v-for="s in status.services" :key="s.name" class="svc" :class="s.status">
          <span class="dot" :class="s.status" />
          <div class="svc-info">
            <div class="svc-t">{{ s.title }}</div>
            <div class="svc-s">{{ s.status === 'up' ? '运行中' : '不可达' }}</div>
          </div>
        </div>
      </div>

      <!-- 累计计数 -->
      <div class="sec-ttl">运行统计（本次后端启动以来）</div>
      <div class="cnt-grid">
        <div class="cnt"><div class="n">{{ fmt(status.counters?.data_processed_total) }}</div><div class="k">累计处理数据点</div></div>
        <div class="cnt"><div class="n">{{ fmt(status.counters?.anomaly_detected_total) }}</div><div class="k">累计检出超标点</div></div>
        <div class="cnt"><div class="n">{{ status.plants.length }}</div><div class="k">接入厂数</div></div>
        <div class="cnt"><div class="n">{{ onlineCount }}</div><div class="k">有数据厂数</div></div>
      </div>

      <!-- 各厂态势 -->
      <div class="sec-ttl">厂站接入态势</div>
      <div class="tbl" v-if="status.plants.length">
        <div class="tr th">
          <span>厂站</span><span>状态</span><span>数据流</span><span>最新数据</span><span>操作</span>
        </div>
        <div v-for="p in status.plants" :key="p.plant_id" class="tr">
          <span class="pid">{{ p.plant_id }}</span>
          <span><i class="dot sm" :class="p.status" />{{ plantStatusLabel(p.status) }}<small class="types"> · {{ contextLabel(p.data_context) }} · {{ p.data_context?.bucket || '数据库未核验' }}<template v-if="p.data_context?.warning"> · {{ p.data_context.warning }}</template></small></span>
          <span class="types">{{ p.data_types.join(' / ') || '—' }}</span>
          <span>{{ formatSamplingTime(p.latest_time, p.data_context?.timezone) }}<small class="types"> · 时效 {{ plantStatusLabel(p.data_context?.freshness || 'unverified') }} · 最新采样 {{ formatSamplingTime(p.data_context?.latest_sample_at, p.data_context?.timezone) }}</small></span>
          <span><button class="lnk" @click="router.push(`/plants/${encodeURIComponent(p.plant_id)}`)">查看看板 →</button></span>
        </div>
      </div>
      <div v-else class="empty">暂无厂站接入（导入报表后自动出现）</div>
    </template>

    </PageState>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import PageState from '@/components/common/PageState.vue'
import { formatDataContext as contextLabel } from '@/utils/displayFormat'
import { usePolling } from '@/composables/usePolling'
import { plantStatusLabel, requestGate, shanghaiTime, formatSamplingTime } from '@/composables/dashboardData'
import type { DataContext } from '@/api/types/api.types'

interface SysStatus {
  generated_at: string
  services: { name: string; title: string; status: 'up' | 'down' }[]
  plants: { plant_id: string; status: string; latest_time: string; data_types: string[]; data_context?: DataContext }[]
  counters: Record<string, number>
}

const router = useRouter()
const status = ref<SysStatus | null>(null)
const loading = ref(false)
const error = ref('')
const viewState = computed(() => loading.value ? (status.value ? 'refreshing' : 'initial-loading') : error.value ? 'error' : status.value ? 'ready' : 'empty')
const onlineCount = computed(() => status.value?.plants.filter((p) => !['offline', 'missing'].includes(p.status) && !!p.latest_time).length ?? 0)
const gate = requestGate()
const fmt = (n?: number) => (n === undefined || n === null ? '—' : n.toLocaleString())

const POLL_MS = 15_000
async function load() {
  const request = gate.begin()
  if (request === null) return
  loading.value = true
  error.value = ''
  try {
    const r = await api.get<unknown, { data: SysStatus }>('/v1/system/status')
    if (gate.current(request)) status.value = r.data
  } catch (e) { if (gate.current(request)) error.value = e instanceof Error ? e.message : '系统态势加载失败' } finally { if (gate.current(request)) loading.value = false }
}
const { start, stop } = usePolling(load, POLL_MS)
const polling = ref(true)
function togglePolling() {
  if (polling.value) { stop(); polling.value = false } else { start(); polling.value = true }
}
onMounted(start)
onBeforeUnmount(() => { gate.dispose(); stop() })
</script>

<style scoped>
.sys { display: flex; flex-direction: column; gap: 10px; max-width: 1100px }
.hd { display: flex; align-items: center; gap: 14px }
.hd h2 { margin: 0; font-size: 18px }
.sub { font-size: 12px; color: var(--text-muted) }
.pause { all: unset; cursor: pointer; font-size: 12px; border: 1px dashed var(--brd); border-radius: 7px; padding: 4px 10px; color: var(--text-secondary) }
.pause.on { color: var(--primary); border-color: var(--primary) }

.sec-ttl { font-size: 12.5px; font-weight: 700; color: var(--text-secondary); margin-top: 8px }

.svc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px }
.svc { display: flex; align-items: center; gap: 10px; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 12px; padding: 12px 14px }
.svc.down { border-color: #fca5a5; background: rgba(239,68,68,.04) }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0 }
.dot.up, .dot.online { background: #10b981; animation: pulse 2s infinite }
.dot.down, .dot.offline { background: #ef4444 }
.dot.sm { width: 7px; height: 7px; display: inline-block; margin-right: 6px }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,.4) } 50% { box-shadow: 0 0 0 5px rgba(16,185,129,0) } }
.svc-t { font-size: 13.5px; font-weight: 600 }
.svc-s { font-size: 11px; color: var(--text-muted) }

.cnt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px }
.cnt { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0); border-radius: 12px; padding: 12px 14px }
.cnt .n { font-size: 22px; font-weight: 800; color: var(--primary, #4f46e5) }
.cnt .k { font-size: 11.5px; color: var(--text-muted); margin-top: 2px }

.tbl { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0); border-radius: 12px; overflow: hidden }
.tr { display: grid; grid-template-columns: 1.6fr .6fr 1fr 1fr .7fr; gap: 8px; padding: 10px 14px;
  font-size: 13px; align-items: center; border-top: 1px solid var(--brd, #eef2f7) }
.tr.th { border-top: 0; font-size: 11.5px; color: var(--text-muted); font-weight: 600; background: #f8fafc }
.pid { font-weight: 600 }
.types { color: var(--text-muted); font-size: 12px }
.lnk { all: unset; cursor: pointer; color: var(--primary); font-size: 12.5px }
.lnk:hover { text-decoration: underline }
.empty, .loading { padding: 40px; text-align: center; color: var(--text-muted); font-size: 13px }
</style>
