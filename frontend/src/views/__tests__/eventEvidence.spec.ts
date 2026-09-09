// frontend/src/views/__tests__/eventEvidence.spec.ts
import { describe, it, expect } from 'vitest'
import { splitEvidence } from '@/views/eventEvidence'

describe('splitEvidence（evidence_points 真结构拆分）', () => {
  const evidence = [
    { category: 'anomaly', indicator: 'COD', value: 501.9, timestamp: '2026-07-14 12:00:00',
      score: 0.78, expected_range: [65.6, 96.2] },
    { category: 'expert_pattern', pattern: '插瓶干扰', pattern_key: 'bottle_interference',
      match_score: 0.9, confidence: 0.95, suspicion_level: 'critical' },
    { category: 'anomaly', indicator: 'TN', value: 4.23, timestamp: '2026-07-14 00:00:00',
      score: 0.79, expected_range: [4.84, 5.435] },
  ]

  it('按 category 拆成指标异常点与模式命中两组', () => {
    const { anomalies, patterns } = splitEvidence(evidence as any)
    expect(anomalies).toHaveLength(2)
    expect(patterns).toHaveLength(1)
    expect(anomalies[0]).toMatchObject({ indicator: 'COD', value: 501.9 })
    expect(patterns[0]).toMatchObject({ pattern: '插瓶干扰', match_score: 0.9 })
  })

  it('未知 category 落入 anomalies 兜底不丢数据', () => {
    const { anomalies, patterns } = splitEvidence([
      { category: 'weird', indicator: 'X' } as any,
    ])
    expect(anomalies).toHaveLength(1)
    expect(patterns).toHaveLength(0)
  })

  it('空数组与 null 安全', () => {
    expect(splitEvidence([])).toEqual({ anomalies: [], patterns: [] })
    expect(splitEvidence(null as any)).toEqual({ anomalies: [], patterns: [] })
  })

  it('非数组（旧后端对象 shape）按空处理不抛错', () => {
    expect(splitEvidence({ dataSnapshot: {} } as any)).toEqual({ anomalies: [], patterns: [] })
  })
})
