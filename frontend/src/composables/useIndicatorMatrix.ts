import type { RealtimeData, HistoryData } from '@/api/types/api.types'
import { classifyTrend, type Trend } from './useSparkline'
import { computeRemovalRates } from './useDerivedMetrics'

export interface IndicatorCell {
  key: string
  name: string
  value: number | null
  unit: string
  deltaPct: number | null
  trend: Trend
  series: number[]
}

export interface IndicatorGroups {
  influent: IndicatorCell[]
  effluent: IndicatorCell[]
  derived: IndicatorCell[]
}

const INDICATORS: { key: string; name: string; unit: string }[] = [
  { key: 'pH', name: 'pH', unit: '' },
  { key: 'COD', name: '化学需氧量', unit: 'mg/L' },
  { key: 'TN', name: '总氮', unit: 'mg/L' },
  { key: 'AN', name: '氨氮', unit: 'mg/L' },
  { key: 'TP', name: '总磷', unit: 'mg/L' },
]

function pct(series: number[]): number | null {
  const s = series.filter((v) => v != null && Number.isFinite(v))
  if (s.length < 2) return null
  const first = s[0], last = s[s.length - 1]
  if (first === 0) return null
  return +(((last - first) / Math.abs(first)) * 100).toFixed(1)
}

function sideCells(side: 'influent' | 'effluent', realtime: RealtimeData, history: HistoryData): IndicatorCell[] {
  return INDICATORS.map(({ key, name, unit }) => {
    const series = history.records
      .map((r) => r[side]?.[key] ?? null)
      .filter((v): v is number => v != null && Number.isFinite(v))
    // For 2-point series, lower minPoints threshold to detect trend
    const trend = series.length === 2 ? classifyTrend(series, { minPoints: 2, slopeThresh: 0.01 }) : classifyTrend(series)
    return { key, name, unit, value: realtime[side]?.[key] ?? null, deltaPct: pct(series), trend, series }
  })
}

function derivedCells(history: HistoryData): IndicatorCell[] {
  const rates = computeRemovalRates(history.records)
  return (['COD', 'TN', 'AN', 'TP'] as const).map((p) => ({
    key: `${p}_removal`, name: `${p} 去除率`, value: rates[p], unit: '%', deltaPct: null, trend: 'flat' as Trend, series: [],
  }))
}

export function buildIndicatorCells(realtime: RealtimeData, history: HistoryData): IndicatorGroups {
  return { influent: sideCells('influent', realtime, history), effluent: sideCells('effluent', realtime, history), derived: derivedCells(history) }
}
