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
// regulation / process_mechanism / similar_case：原始对象原样进（字段异构，不做筛选）
export type EvidenceOther = Record<string, unknown>

/** 上游 rule_reasoning 已知的三类"非指标非模式"证据类别 → 中文标签 */
export const OTHER_CATEGORY_LABELS: Record<string, string> = {
  regulation: '法规条款',
  process_mechanism: '工艺机理',
  similar_case: '同类案例',
}
const OTHER_CATEGORIES = new Set(Object.keys(OTHER_CATEGORY_LABELS))

export function splitEvidence(evidence: Record<string, unknown>[] | null | undefined): {
  anomalies: EvidenceAnomaly[]
  patterns: EvidencePattern[]
  others: EvidenceOther[]
} {
  const anomalies: EvidenceAnomaly[] = []
  const patterns: EvidencePattern[] = []
  const others: EvidenceOther[] = []
  // 非数组（旧后端对象 shape / schema 漂移）按空处理，不让详情抽屉整块崩
  const list: Record<string, unknown>[] = Array.isArray(evidence) ? evidence : []
  for (const e of list) {
    // null 元素（上游聚合瑕疵）跳过，不炸整块渲染
    if (e == null) continue
    const category = e.category as string
    if (category === 'expert_pattern') {
      patterns.push({
        pattern: String(e.pattern ?? ''),
        pattern_key: String(e.pattern_key ?? ''),
        match_score: typeof e.match_score === 'number' ? e.match_score : null,
        confidence: typeof e.confidence === 'number' ? e.confidence : null,
        suspicion_level: String(e.suspicion_level ?? ''),
      })
    } else if (OTHER_CATEGORIES.has(category)) {
      // 法规/工艺机理/同类案例：结构异构，原样保留由「其他证据」小节按键值渲染
      others.push(e)
    } else {
      // anomaly 及未知/缺失 category 兜底（不丢数据）
      anomalies.push({
        indicator: String(e.indicator ?? ''),
        timestamp: String(e.timestamp ?? ''),
        value: typeof e.value === 'number' ? e.value : null,
        score: typeof e.score === 'number' ? e.score : null,
        expected_range: Array.isArray(e.expected_range) ? (e.expected_range as number[]) : null,
      })
    }
  }
  return { anomalies, patterns, others }
}
