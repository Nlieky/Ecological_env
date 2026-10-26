export interface DashboardRecord { timestamp: string; influent: Record<string, number | null>; effluent: Record<string, number | null> }
type Series = Record<string, { series: { influent: { time: string; value: number | null }[]; effluent: { time: string; value: number | null }[] } }>
export function advanceDate(date: string, days: number) {
  dateRange(date, date)
  const calendar = new Date(`${date}T00:00:00Z`)
  calendar.setUTCDate(calendar.getUTCDate() + days)
  return calendar.toISOString().slice(0, 10)
}
export function formatSamplingTime(time?: string | null, timezone?: string) {
  if (!time) return `—（${timezone || '时区未核验'}）`
  let formatted = time.replace('T', ' ')
  if (timezone && /(Z|[+-]\d{2}:?\d{2})$/.test(time)) {
    try { formatted = new Intl.DateTimeFormat('sv-SE', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(new Date(time)) } catch { return `${formatted}（时区未核验）` }
  }
  return `${formatted}（${timezone || '时区未核验'}）`
}
export function shortSamplingTime(time: string, timezone = 'Asia/Shanghai') {
  return time ? formatSamplingTime(time, timezone).slice(5, 16) : '—'
}
export function dashboardSnapshot<T extends { indicators: Series }>(dashboard: T): { dashboard: T; records: DashboardRecord[] } { return { dashboard, records: dashboardRecords(dashboard.indicators) } }
export function shanghaiTime(time?: string | null) {
  if (!time) return '—'
  if (!/(Z|[+-]\d{2}:?\d{2})$/.test(time)) return time.replace('T', ' ')
  const date = new Date(time)
  if (Number.isNaN(date.getTime())) return time
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(date)
}
export function dashboardRecords(indicators: Series): DashboardRecord[] {
  const rows = new Map<string, DashboardRecord>()
  for (const [key, indicator] of Object.entries(indicators)) for (const side of ['influent', 'effluent'] as const) {
    for (const point of indicator.series[side]) {
      const timestamp = point.time.replace(' ', 'T')
      const row = rows.get(timestamp) ?? { timestamp, influent: {}, effluent: {} }
      row[side][key] = typeof point.value === 'number' && Number.isFinite(point.value) ? point.value : null
      rows.set(timestamp, row)
    }
  }
  return [...rows.values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
}
export function latestValues(rows: DashboardRecord[], key: string): { influent: number | null; effluent: number | null } {
  const result = { influent: null, effluent: null } as { influent: number | null; effluent: number | null }
  for (const row of rows) for (const side of ['influent', 'effluent'] as const) {
    const value = row[side][key]
    if (typeof value === 'number' && Number.isFinite(value)) result[side] = value
  }
  return result
}
export function annotationCursor(rows: DashboardRecord[], timestamp: string, cursor: number, windowPoints: number) {
  const index = rows.findIndex(row => row.timestamp === timestamp.replace(' ', 'T'))
  if (index < 0 || (index >= cursor - windowPoints && index < cursor)) return cursor
  return Math.min(index + Math.max(1, Math.floor(windowPoints / 2)), rows.length)
}
export function finiteStats(values: unknown[]) {
  const finite = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
  return finite.length ? { mean: finite.reduce((sum, v) => sum + v, 0) / finite.length, min: Math.min(...finite), max: Math.max(...finite) } : { mean: null, min: null, max: null }
}
export function dateRange(start: string, end: string) {
  const valid = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s)) && new Date(s).toISOString().slice(0, 10) === s
  if (!valid(start) || (end && !valid(end))) throw new Error('请输入有效日期')
  if (end && end < start) throw new Error('结束日期不能早于开始日期')
  return { anchor: start, endDate: end || start }
}
export function contextLabel(context?: { origin: string; mode: string }) {
  const origins: Record<string, string> = { real: '真实数据', simulated: '模拟数据', unverified: '来源未核验' }
  const modes: Record<string, string> = { historical: '历史数据', simulation: '仿真数据', live: '实时数据', unverified: '模式未核验' }
  return `${origins[context?.origin ?? 'unverified'] ?? '来源未核验'} · ${modes[context?.mode ?? 'unverified'] ?? '模式未核验'}`
}
export function plantStatusLabel(status: string) {
  return ({ historical: '历史数据', simulation: '模拟数据', fresh: '近期数据', stale: '数据已过期', future: '未来时间数据', missing: '无数据', unverified: '时效未核验', online: '有数据（时效未核验）', offline: '无数据' } as Record<string, string>)[status] ?? '时效未核验'
}
export function requestGate() {
  let generation = 0; let disposed = false
  return { alive: () => !disposed, begin: (): number | null => disposed ? null : ++generation, current: (id: number | null) => !disposed && id === generation, dispose: () => { disposed = true; generation++ } }
}
export async function initializeMetrics(fetchTree: () => Promise<unknown>, gate: ReturnType<typeof requestGate>, selectPlant: () => void, load: () => Promise<unknown>) {
  if (!gate.alive()) return
  await fetchTree()
  if (!gate.alive()) return
  selectPlant()
  if (gate.alive()) await load()
}
