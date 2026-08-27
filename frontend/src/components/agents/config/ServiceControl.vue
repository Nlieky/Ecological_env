<template>
  <div class="sc">
    <div class="sc-card">
      <div class="sc-h">Agent 服务（端口 {{ status?.port || 8642 }}）</div>
      <div class="sc-row">
        <span class="sc-k">状态</span>
        <span class="sc-v" :class="status?.alive ? 'ok' : 'bad'">
          {{ restarting ? '重启中…' : (status?.alive ? '● 运行中' : '● 已停止') }}
        </span>
      </div>
      <div class="sc-row"><span class="sc-k">进程 PID</span>
        <span class="sc-v mono">{{ status?.pids?.length ? status.pids.join(', ') : '—' }}</span></div>
      <div class="sc-row"><span class="sc-k">模型</span>
        <span class="sc-v mono">{{ status?.model || '—' }}</span></div>
      <div class="sc-acts">
        <button class="btn primary" @click="doRestart" :disabled="restarting">
          {{ restarting ? `重启中（${pollSec}s）…` : '一键重启' }}
        </button>
        <button class="btn" @click="refresh" :disabled="restarting">刷新状态</button>
      </div>
      <div v-if="lastResult" class="sc-res" :class="lastResult.ok ? 'ok' : 'bad'">
        {{ lastResult.ok ? `✓ 已重启（旧 PID ${lastResult.old_pids?.length ? lastResult.old_pids.join(', ') : '无'}）` +
           (lastResult.new_alive ? '' : ' ⚠ health 未就绪，请看 agent 控制台日志') : `✗ ${lastResult.error}` }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService } from '@/api/modules/agentConfig'

interface SvcStatus { alive: boolean; port: number; pids: number[]; model: string }
const status = ref<SvcStatus | null>(null)
const restarting = ref(false)
const pollSec = ref(0)
const lastResult = ref<{ ok: boolean; old_pids?: number[]; new_alive?: boolean; error?: string } | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

async function refresh() {
  try {
    const r: any = await agentConfigService.serviceStatus()
    status.value = (r?.data ?? r) as SvcStatus
  } catch { status.value = null }
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
  try {
    await ElMessageBox.confirm('重启会中断正在进行的查询，确认重启 agent 服务？', '确认重启', { type: 'warning' })
  } catch { return }
  restarting.value = true; lastResult.value = null
  startCountdown()
  try {
    const r: any = await agentConfigService.serviceRestart()
    lastResult.value = r
    if (r?.ok && r?.new_alive) ElMessage.success('agent 服务已重启')
    else if (r?.ok) ElMessage.warning('进程已启动但 health 未就绪——请看 agent 控制台日志')
    else ElMessage.error('重启失败：' + (r?.error || '未知'))
  } catch (e: any) { ElMessage.error('重启请求失败：' + (e?.message || e)) }
  finally {
    stopCountdown()
    restarting.value = false
    await refresh()
  }
}

onMounted(refresh)
onUnmounted(stopCountdown)
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
