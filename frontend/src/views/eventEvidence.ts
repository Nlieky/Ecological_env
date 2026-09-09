// frontend/src/views/eventEvidence.ts
/** evidence_points 真结构 → 详情抽屉渲染数据的纯转换（后端 Task2 契约） */
export interface EvidenceAnomaly {
  indicator: string
  timestamp: string
  value: number | null
  score: number | null
  expected_range: number[] | null
}
export interface EvidencePattern {
  pattern: string
  pattern_key: string
  match_score: number | null
  confidence: number | null
  suspicion_level: string
}

export function splitEvidence(evidence: Record<string, unknown>[] | null | undefined): {
  anomalies: EvidenceAnomaly[]
  patterns: EvidencePattern[]
} {
  const anomalies: EvidenceAnomaly[] = []
  const patterns: EvidencePattern[] = []
  // 非数组（旧后端对象 shape / schema 漂移）按空处理，不让详情抽屉整块崩
  const list: Record<string, unknown>[] = Array.isArray(evidence) ? evidence : []
  for (const e of list) {
    if ((e?.category as string) === 'expert_pattern') {
      patterns.push({
        pattern: String(e.pattern ?? ''),
        pattern_key: String(e.pattern_key ?? ''),
        match_score: typeof e.match_score === 'number' ? e.match_score : null,
        confidence: typeof e.confidence === 'number' ? e.confidence : null,
        suspicion_level: String(e.suspicion_level ?? ''),
      })
    } else {
      // anomaly 及未知 category 兜底（不丢数据）
      anomalies.push({
        indicator: String(e?.indicator ?? ''),
        timestamp: String(e?.timestamp ?? ''),
        value: typeof e?.value === 'number' ? e.value : null,
        score: typeof e?.score === 'number' ? e.score : null,
        expected_range: Array.isArray(e?.expected_range) ? (e.expected_range as number[]) : null,
      })
    }
  }
  return { anomalies, patterns }
}
