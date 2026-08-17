import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Annotation {
  timestamp: string
  value: number
  type: string
  segment?: string
}

/** 动作指令数据（主智能体 action-command-core 技能输出） */
export interface ActionData {
  cmd: string
  indicators?: string[]
  side?: 'influent' | 'effluent' | 'all'
  range?: '1h' | '6h' | '24h' | '7d' | '30d'
  date?: string
  annotations?: Annotation[]
  [k: string]: unknown
}

/**
 * 大屏动作状态——AI 助手的动作指令经 chat store 的 onAction 回调 dispatch 到这里，
 * 各视图 watch 本 store 的字段响应（MetricsView 切指标/时间/渲染标注）。
 */
export const useActionStore = defineStore('action', () => {
  /** 大屏当前指标(null=全部) */
  const indicators = ref<string[] | null>(null)
  /** 大屏当前进出水(null=全部) */
  const side = ref<'influent' | 'effluent' | null>(null)
  /** 大屏时间范围 */
  const timeRange = ref<'1h' | '6h' | '24h' | '7d' | '30d' | null>(null)
  /** 单日视图日期(YYYY-MM-DD) */
  const date = ref<string | null>(null)
  /** 算法标注(曲线高亮) */
  const annotations = ref<Annotation[]>([])
  /** 最后一次动作(供 UI 提示) */
  const lastAction = ref<string>('')

  function dispatch(action: ActionData) {
    lastAction.value = action.cmd
    switch (action.cmd) {
      case 'set_view':
        indicators.value = action.indicators ?? null
        side.value = action.side === 'all' ? null : (action.side ?? null)
        break
      case 'set_time_range':
        if (action.range) timeRange.value = action.range
        if (action.date) date.value = action.date
        break
      case 'run_detector':
        annotations.value = action.annotations ?? []
        break
      default:
        console.warn('[ActionDispatcher] 未知 cmd，忽略:', action.cmd)
    }
  }

  function clearAnnotations() {
    annotations.value = []
  }

  return { indicators, side, timeRange, date, annotations, lastAction, dispatch, clearAnnotations }
})
