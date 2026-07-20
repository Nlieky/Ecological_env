import { describe, it, expect } from 'vitest'
import { computeRemovalRates } from '../useDerivedMetrics'
import type { HistoryRecord } from '@/api/types/api.types'

const recs: HistoryRecord[] = [
  { timestamp: 't1', influent: { COD: 100, TN: 20, AN: 5, TP: 2, pH: 7 }, effluent: { COD: 50, TN: 10, AN: 2, TP: 1, pH: 7 } },
  { timestamp: 't2', influent: { COD: 80, TN: 16, AN: 4, TP: 2, pH: 7 }, effluent: { COD: 40, TN: 8, AN: 2, TP: 1, pH: 7 } },
]

describe('computeRemovalRates', () => {
  it('各污染物去除率 = mean((in-out)/in),范围 [0,1]', () => {
    const r = computeRemovalRates(recs)
    expect(r.COD).toBeCloseTo(0.5, 2)   // (100-50)/100=0.5, (80-40)/80=0.5 -> 0.5
    expect(r.TN).toBeCloseTo(0.5, 2)
    expect(r.AN).toBeCloseTo(0.55, 2)   // (5-2)/5=0.6, (4-2)/4=0.5 -> 0.55
    expect(r.TP).toBeCloseTo(0.5, 2)
  })
  it('缺数据(进水 null)跳过该配对', () => {
    const r = computeRemovalRates([{ timestamp: 't', influent: { COD: null as any, TN: 10, AN: 0, TP: 0, pH: 7 }, effluent: { COD: 10, TN: 5, AN: 0, TP: 0, pH: 7 } }])
    expect(r.COD).toBeNull()
    expect(r.TN).toBeCloseTo(0.5, 2)
  })
  it('进水为 0 时去除率 null(除零)', () => {
    const r = computeRemovalRates([{ timestamp: 't', influent: { COD: 0, TN: 0, AN: 0, TP: 0, pH: 7 }, effluent: { COD: 0, TN: 0, AN: 0, TP: 0, pH: 7 } }])
    expect(r.COD).toBeNull()
  })
})
