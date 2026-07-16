import { ref } from 'vue'
import type { DecisionPath } from '@/api/types/api.types'

export interface EvidenceItem {
  type: string
  description: string
  stepNumber: number
}

export function useEvidenceChain() {
  const expanded = ref(false)

  const formatEvidence = (decisionPath: DecisionPath[]): EvidenceItem[] => {
    return decisionPath.map(step => ({
      type: step.step_name,
      description: `${step.decision} → ${step.action}`,
      stepNumber: step.step_number
    }))
  }

  const toggleExpanded = () => {
    expanded.value = !expanded.value
  }

  return {
    expanded,
    formatEvidence,
    toggleExpanded
  }
}
