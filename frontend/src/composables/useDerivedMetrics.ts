import type { HistoryRecord } from '@/api/types/api.types'

const POLLUTANTS = ['COD', 'TN', 'AN', 'TP'] as const
type Pollutant = typeof POLLUTANTS[number]
export type RemovalRates = Record<Pollutant, number | null>

/** 各污染物去除率 = 配对样本 mean((in-out)/in);进水 0 或无配对返回 null。 */
export function computeRemovalRates(records: HistoryRecord[]): RemovalRates {
  const out = {} as RemovalRates
  for (const p of POLLUTANTS) {
    const pairs: number[] = []
    for (const r of records) {
      const i = r.influent?.[p]
      const o = r.effluent?.[p]
      if (i == null || o == null || i === 0) continue
      pairs.push((i - o) / i)
    }
    out[p] = pairs.length ? clamp01(pairs.reduce((a, b) => a + b, 0) / pairs.length) : null
  }
  return out
}

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return null as any
  return Math.max(0, Math.min(1, v))
}
