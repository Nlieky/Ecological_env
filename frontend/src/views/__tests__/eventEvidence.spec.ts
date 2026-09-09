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

  it('5 类混合 + 未知类三分桶：regulation 进 others 不进 anomalies', () => {
    const regulation = { category: 'regulation', indicator: 'COD', regulation: '污水综合排放标准',
      regulation_code: 'GB 8978', violation_type: '超标排放', article: '表2', penalty: '限期治理',
      evidence: '实测 501.9 超标准限值' }
    const process = { category: 'process_mechanism', indicator: 'TN', detail: '碳氮比与反硝化机理不符' }
    const similar = { category: 'similar_case', case: '某厂稀释排放案', similarity: 0.88, conclusion: '确认违规' }
    const { anomalies, patterns, others } = splitEvidence([
      { category: 'anomaly', indicator: 'COD', value: 501.9, timestamp: '2026-07-14 12:00:00',
        score: 0.78, expected_range: [65.6, 96.2] },
      { category: 'expert_pattern', pattern: '插瓶干扰', pattern_key: 'bottle_interference',
        match_score: 0.9, confidence: 0.95, suspicion_level: 'critical' },
      regulation,
      process,
      similar,
      { category: 'weird_new_type', indicator: 'X' },
    ] as any)
    // anomaly + 未知类 → anomalies 兜底（不丢数据）
    expect(anomalies).toHaveLength(2)
    expect(anomalies.map((a) => a.indicator)).toEqual(['COD', 'X'])
    expect(patterns).toHaveLength(1)
    // regulation / process_mechanism / similar_case → others
    expect(others).toHaveLength(3)
    // 原始对象原样进 others，不筛选字段
    expect(others[0]).toEqual(regulation)
    expect(others[1]).toEqual(process)
    expect(others[2]).toEqual(similar)
  })

  it('未知 category 落入 anomalies 兜底不丢数据', () => {
    const { anomalies, patterns, others } = splitEvidence([
      { category: 'weird', indicator: 'X' } as any,
    ])
    expect(anomalies).toHaveLength(1)
    expect(patterns).toHaveLength(0)
    expect(others).toHaveLength(0)
  })

  it('数组含 null 元素不炸且被跳过', () => {
    const { anomalies, patterns, others } = splitEvidence([
      null,
      { category: 'anomaly', indicator: 'COD', value: 501.9, score: 0.78 },
      null,
      { category: 'regulation', regulation: 'GB 8978' },
    ] as any)
    expect(anomalies).toHaveLength(1)
    expect(anomalies[0].indicator).toBe('COD')
    expect(patterns).toHaveLength(0)
    expect(others).toHaveLength(1)
  })

  it('空数组与 null 安全', () => {
    expect(splitEvidence([])).toEqual({ anomalies: [], patterns: [], others: [] })
    expect(splitEvidence(null as any)).toEqual({ anomalies: [], patterns: [], others: [] })
  })

  it('非数组（旧后端对象 shape）按空处理不抛错', () => {
    expect(splitEvidence({ dataSnapshot: {} } as any)).toEqual({ anomalies: [], patterns: [], others: [] })
  })
})
