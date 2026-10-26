import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AnnotationContext } from '@/assistant/annotations'

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
  plant?: string
  indicator?: string
  algorithm?: string
  time_range?: string
  annotations?: Annotation[]
  [k: string]: unknown
}

/** 大屏当前观看窗口上下文——AI 检测动作按"用户正在看的时段"取数 */
export interface ViewContext {
  plant?: string
  /** 开播锚点日期(YYYY-MM-DD);'' = 实时模式 */
  anchor?: string
  /** 当前段起止(YYYY-MM-DD HH:MM),实时模式=最新点窗口 */
  segmentStart?: string
  segmentEnd?: string
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
  /** 算法标注(曲线高亮);按指标分组存,大屏各面板只取自己指标的标注 */
  const annotations = ref<Annotation[]>([])
  /** 标注所属指标(run_detector 单指标检测时大屏只标该面板) */
  const annotationIndicator = ref<string | null>(null)
  const annotationContext = ref<AnnotationContext | null>(null)
  const annotationSide = ref<'influent' | 'effluent'>('effluent')
  /** 标注时间戳版本号(每次新标注+1,供视图watch触发) */
  const annotationSeq = ref(0)
  /** 最后一次动作(供 UI 提示) */
  const lastAction = ref<string>('')
  /** 动作目标厂(null=当前厂) */
  const plant = ref<string | null>(null)
  /** 大屏当前观看窗口(PlantBoardPanel 每次 fetch 后更新;chat 请求带给后端) */
  const viewContext = ref<ViewContext>({})

  /** 大屏调用:记录当前观看窗口,供 AI 检测动作对齐 */
  function setViewContext(ctx: ViewContext) {
    viewContext.value = ctx
  }

  function dispatch(action: ActionData) {
    lastAction.value = action.cmd
    if (action.plant) plant.value = action.plant
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
        void acceptDetection(action)
        break
      default:
        console.warn('[ActionDispatcher] 未知 cmd，忽略:', action.cmd)
    }
  }

  /** 检测结果落地:LLM 给的窗口若与当前观看窗口不重叠 → 用观看窗口重测(后端直调,1-3s) */
  async function acceptDetection(action: ActionData) {
    let ann = action.annotations ?? []
    const tr = String(action.time_range || '')
    const vc = viewContext.value
    // 窗口校验:观看窗口(段)与检测结果 time_range 完全不重叠 → LLM 检错时段,重测
    const overlap = !vc.segmentStart || !tr
      || tr.slice(0, 16) <= (vc.segmentEnd || '').slice(0, 16)
        && tr.slice(-16) >= (vc.segmentStart || '').slice(0, 16)
    if (!overlap && vc.segmentStart) {
      try {
        const api = (await import('@/api/client')).default
        const r = await api.post<unknown, { success: boolean; data: any }>('/v1/detection/run', {
          algorithm: String(action.algorithm || 'constant'),
          indicator: String(action.indicator || 'pH'),
          start: vc.segmentStart, end: vc.segmentEnd || 'now',
          side: String(action.side || 'effluent'),
          plant: String(action.plant || vc.plant || ''),
        })
        if (r?.success && r.data?.actionData?.annotations) {
          ann = r.data.actionData.annotations
        }
      } catch { /* 重测失败就用 LLM 原结果 */ }
    }
    annotations.value = ann
    annotationContext.value = null
    annotationSide.value = action.side === 'influent' ? 'influent' : 'effluent'
    annotationIndicator.value = action.indicator ? normalizeIndicator(action.indicator) : null
    annotationSeq.value++
  }

  /** 中文/别名指标名 → 看板字段(pH/COD/TN/AN/TP/suspended_solids) */
  function normalizeIndicator(name: string): string {
    const map: Record<string, string> = {
      'pH': 'pH', 'PH': 'pH', 'ph': 'pH',
      'COD': 'COD', 'cod': 'COD', '化学需氧量': 'COD',
      'TN': 'TN', 'tn': 'TN', '总氮': 'TN',
      'AN': 'AN', '氨氮': 'AN', 'NH3-N': 'AN', 'NH3N': 'AN', 'nh3n': 'AN',
      'TP': 'TP', 'tp': 'TP', '总磷': 'TP',
      'SS': 'suspended_solids', 'ss': 'suspended_solids', '悬浮物': 'suspended_solids',
    }
    return map[name.trim()] ?? name
  }

  function clearAnnotations() {
    annotations.value = []
    annotationContext.value = null
    annotationIndicator.value = null
    annotationSeq.value++
  }

  return { indicators, side, timeRange, date, annotations, annotationIndicator, annotationContext, annotationSide, annotationSeq,
    plant, lastAction, viewContext, setViewContext, dispatch, clearAnnotations, normalizeIndicator }
})
