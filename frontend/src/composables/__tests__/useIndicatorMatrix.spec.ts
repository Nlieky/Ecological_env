import { describe, it, expect } from 'vitest'
import { buildIndicatorCells } from '../useIndicatorMatrix'
import type { RealtimeData, HistoryData } from '@/api/types/api.types'

const realtime: RealtimeData = {
  timestamp: 't2', flow_rate: 300, quality_score: 0.99,
  influent: { pH: 7, COD: 80, TN: 16, AN: 4, TP: 2 },
  effluent: { pH: 7, COD: 40, TN: 8, AN: 2, TP: 1 },
}
const history: HistoryData = {
  total_count: 2, page: 1, page_size: 50, summary: {},
  records: [
    { timestamp: 't1', influent: { pH: 7, COD: 100, TN: 20, AN: 5, TP: 2 }, effluent: { pH: 7, COD: 50, TN: 10, AN: 2, TP: 1 } },
    { timestamp: 't2', influent: { pH: 7, COD: 80, TN: 16, AN: 4, TP: 2 }, effluent: { pH: 7, COD: 40, TN: 8, AN: 2, TP: 1 } },
  ],
}

describe('buildIndicatorCells', () => {
  it('进水/出水各含 pH,COD,TN,AN,TP', () => {
    const g = buildIndicatorCells(realtime, history)
    expect(g.influent.map(c => c.key)).toEqual(['pH', 'COD', 'TN', 'AN', 'TP'])
    expect(g.effluent.map(c => c.key)).toEqual(['pH', 'COD', 'TN', 'AN', 'TP'])
  })
  it('格子 value 取 realtime 当前值;series 取 history 该列', () => {
    const g = buildIndicatorCells(realtime, history)
    const cod = g.influent.find(c => c.key === 'COD')!
    expect(cod.value).toBe(80)
    expect(cod.series).toEqual([100, 80])
  })
  it('下降序列 trend=down', () => {
    const g = buildIndicatorCells(realtime, history)
    expect(g.influent.find(c => c.key === 'COD')!.trend).toBe('down')
  })
  it('衍生组含 COD/TN/AN/TP 去除率', () => {
    const g = buildIndicatorCells(realtime, history)
    expect(g.derived.map(c => c.key)).toContain('COD_removal')
    expect(g.derived.find(c => c.key === 'COD_removal')!.value).toBeCloseTo(0.5, 2)
  })
})
