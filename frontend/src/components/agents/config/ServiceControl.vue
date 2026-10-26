<template>
  <div class="sc">
    <div class="sc-card">
      <div class="sc-h">Agent 服务（端口 {{ status?.port || 8642 }}）</div>
      <div class="sc-row">
        <span class="sc-k">状态</span>
        <span class="sc-v" :class="!statusError && !restarting && status?.ready ? 'ok' : 'bad'">
          {{ restarting ? '重启中…' : statusError ? '状态读取失败（显示上次结果）' : !status ? '状态未知' : status.ready ? '● 已就绪' : status.alive ? '● 可连接，尚未就绪' : '● 不可连接' }}
        </span>
      </div>
      <div class="sc-row"><span class="sc-k">进程 PID</span>
        <span class="sc-v mono">{{ status?.pids?.length ? status.pids.join(', ') : '—' }}</span></div>
      <div class="sc-row"><span class="sc-k">已保存兜底模型</span>
        <span class="sc-v mono">{{ status?.saved_model || status?.model || '—' }}</span></div>
      <p>模型来自保存的 llm_model 兜底值，未验证运行中供应商实际加载的模型。</p>
      <p v-if="statusError">{{ statusError }}；请刷新重试。</p>
      <div class="sc-acts">
        <button class="btn primary" @click="doRestart" :disabled="restarting || confirming">
          {{ restarting ? `重启中（${pollSec}s）…` : '一键重启' }}
        </button>
        <button class="btn" @click="refresh" :disabled="restarting">刷新状态</button>
      </div>
      <div v-if="lastResult" class="sc-res" :class="lastResult.ok && lastResult.new_ready === true ? 'ok' : 'bad'">
        {{ lastResult.ok && lastResult.new_ready === true ? '✓ 已重启并就绪' : lastResult.new_alive ? '⚠ 服务可连接，但尚未就绪：' + (lastResult.warn || lastResult.error || '请查看 agent 日志') : '✗ ' + (lastResult.error || '重启未完成') }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type ServiceStatus } from '@/api/modules/agentConfig'
import { requireSuccess } from '@/composables/useConfigDraft'

const status = ref<ServiceStatus | null>(null)
const statusError = ref('')
let disposed = false
let refreshGeneration = 0
const restarting = ref(false)
const confirming = ref(false)
const pollSec = ref(0)
const lastResult = ref<{ ok: boolean; old_pids?: number[]; new_alive?: boolean; new_ready?: boolean; error?: string; warn?: string } | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

async function refresh() {
  const generation = ++refreshGeneration
  try {
    const r: any = await agentConfigService.serviceStatus()
    if (disposed || generation !== refreshGeneration) return
    requireSuccess(r)
    status.value = r.data
    statusError.value = ''
  } catch (e: any) { if (!disposed && generation === refreshGeneration) statusError.value = e?.message || '状态读取失败' }
}

function startCountdown() {
  // 后端最多轮询 health 60s + kill 5s，前端 65s 倒计时给用户感知
  pollSec.value = 65
  timer = setInterval(() => { if (pollSec.value > 0) pollSec.value-- }, 1000)
}
function stopCountdown() {
  if (timer) { clearInterval(timer); timer = null }
  pollSec.value = 0
}

async function doRestart() {
  if (disposed || restarting.value || confirming.value) return
  confirming.value = true
  try {
    await ElMessageBox.confirm('重启会中断正在进行的查询，确认重启 agent 服务？', '确认重启', { type: 'warning' })
  } catch { return }
  finally { confirming.value = false }
  if (disposed) return
  restarting.value = true; lastResult.value = null
  startCountdown()
  try {
    const r: any = await agentConfigService.serviceRestart()
    if (disposed) return
    lastResult.value = r
    if (r?.ok && r?.new_ready === true) ElMessage.success('agent 服务已重启并就绪')
    else if (r?.new_alive) ElMessage.warning('服务可连接但尚未就绪——请看 agent 控制台日志')
    else ElMessage.error('重启失败：' + (r?.error || '未知'))
  } catch (e: any) { if (!disposed) ElMessage.error('重启请求失败：' + (e?.message || e)) }
  finally {
    stopCountdown()
    if (!disposed) { restarting.value = false; await refresh() }
  }
}

onMounted(refresh)
onUnmounted(() => { disposed = true; stopCountdown() })
</script>

<style scoped>
.sc { max-width: 560px }
.sc-card { border: 1px solid var(--brd); border-radius: 13px; padding: 18px }
.sc-h { font-size: 14px; font-weight: 700; margin-bottom: 14px }
.sc-row { display: flex; padding: 7px 0; font-size: 13px }
.sc-k { width: 90px; color: var(--text-muted) }
.sc-v.ok { color: #047857; font-weight: 600 }
.sc-v.bad { color: #dc2626; font-weight: 600 }
.mono { font-family: ui-monospace, monospace; font-size: 12.5px }
.sc-acts { display: flex; gap: 9px; margin-top: 14px }
.btn { font-size: 12.5px; padding: 6px 15px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
.sc-res { margin-top: 12px; font-size: 12.5px; padding: 9px 12px; border-radius: 8px }
.sc-res.ok { background: #ecfdf5; color: #047857 }
.sc-res.bad { background: #fef2f2; color: #dc2626 }
</style>
