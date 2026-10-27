import { plantStatusLabel, shanghaiTime } from '../composables/dashboardData'

export function formatValue(value: unknown): string {
  return value == null || value === '' || (typeof value === 'number' && !Number.isFinite(value)) ? '—' : String(value)
}
export function formatDateTime(value?: string | null): string {
  if (!value || Number.isNaN(Date.parse(value))) return '—'
  return shanghaiTime(value)
}
/** Input duration is milliseconds. */
export function formatDuration(value?: number | null): string {
  if (value == null || !Number.isFinite(value) || value < 0) return '—'
  if (value < 1000) return `${Math.floor(value)}ms`
  const seconds = Math.floor(value / 1000)
  return seconds < 60 ? `${seconds}秒` : `${Math.floor(seconds / 60)}分${String(seconds % 60).padStart(2, '0')}秒`
}
export function formatDataContext(context?: { origin: string; mode: string; freshness?: string }): string {
  const origins: Record<string, string> = { real: '真实导入', imported: '真实导入', real_import: '真实导入', api: '实时接口', live_api: '实时接口', simulated: '模拟数据', simulation: '模拟数据' }
  const modes: Record<string, string> = { historical: '历史数据', simulation: '模拟回放', live: '实时数据' }
  return `${origins[context?.origin ?? ''] ?? '来源未核验'} · ${modes[context?.mode ?? ''] ?? '模式未核验'} · ${plantStatusLabel(context?.freshness ?? 'unverified')}`
}
export function formatRisk(risk?: string | null, humanConfirmed = false): string {
  if (!risk) return '—'
  if (['violation', 'suspected_violation', '违规', '违规嫌疑'].includes(risk)) return humanConfirmed ? '已确认违规' : '违规嫌疑'
  return ({ high: '高风险', medium: '中风险', low: '低风险', normal: '正常', unknown: '风险未核验' } as Record<string, string>)[risk] ?? '风险未核验'
}
export function formatAgentStatus(status?: string | null): string {
  return ({ running: '运行中', idle: '空闲', pending: '等待中', queued: '排队中', cancelled: '接收已停止', completed: '已完成', success: '已完成', failed: '失败', error: '异常', stopped: '已停止', disabled: '已停用', unavailable: '不可用' } as Record<string, string>)[status ?? ''] ?? '状态未核验'
}
export function formatServiceStatus(status?: string | null): string {
  return ({ up: '运行正常', down: '服务不可达', initializing: '初始化中', unconfigured: '尚未配置', online: '在线', healthy: '正常', degraded: '服务降级', offline: '离线', unavailable: '不可用', disabled: '已停用', error: '异常' } as Record<string, string>)[status ?? ''] ?? '状态未核验'
}
