// frontend/src/stores/__tests__/knowledge.impact.spec.ts
// vitest 环境是 node（无 DOM），ElMessage 需 document——mock 掉（runImpact 失败 / highlightCase 无链路分支用到）
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), info: vi.fn() } }))

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useKnowledgeStore, impactNodeStyle, caseLinkNodesOf } from '@/stores/knowledge'

describe('impact store 状态机', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('runImpact 存结果并标记模式', async () => {
    const store = useKnowledgeStore()
    store._impactApi = vi.fn().mockResolvedValue({
      node: { id: 'service:influxdb', type: 'service', label: 'InfluxDB', props: {} },
      downstream: [{ id: 'agent:perception', type: 'agent', label: '感知', depth: 1, via: 'reads' }],
      upstream: [],
    })
    await store.runImpact('service:influxdb')
    expect(store.impactMode).toBe(true)
    expect(store.impactResult?.nodeId).toBe('service:influxdb')
    expect(store.impactResult?.downstream).toHaveLength(1)
  })

  it('runImpact 失败退回普通点击', async () => {
    const store = useKnowledgeStore()
    store._impactApi = vi.fn().mockRejectedValue(new Error('boom'))
    await store.runImpact('service:influxdb')
    expect(store.impactResult).toBeNull()
  })

  it('clearImpact 重置', () => {
    const store = useKnowledgeStore()
    store.impactResult = { nodeId: 'x', node: null, downstream: [], upstream: [] } as any
    store.impactMode = true
    store.clearImpact()
    expect(store.impactMode).toBe(false)
    expect(store.impactResult).toBeNull()
  })

  it('切 tab 清推演（领域 tab 无推演）', () => {
    const store = useKnowledgeStore()
    store.impactMode = true
    store.setTab('domain')
    expect(store.impactMode).toBe(false)
  })

  it('toggleImpactMode 关时清结果', () => {
    const store = useKnowledgeStore()
    store.impactResult = { nodeId: 'x', node: null, downstream: [], upstream: [] } as any
    store.toggleImpactMode()  // true→false
    expect(store.impactResult).toBeNull()
  })
})

describe('impactNodeStyle 着色纯函数', () => {
  const result: any = {
    nodeId: 'svc:a',
    downstream: [{ id: 'n:down' }, { id: 'n:down2' }],
    upstream: [{ id: 'n:up' }],
  }

  it('fault/affected/candidate/unrelated 四态', () => {
    expect(impactNodeStyle('svc:a', result).state).toBe('fault')
    expect(impactNodeStyle('n:down', result).state).toBe('affected')
    expect(impactNodeStyle('n:up', result).state).toBe('candidate')
    expect(impactNodeStyle('n:other', result).state).toBe('unrelated')
  })

  it('无推演结果 = normal', () => {
    expect(impactNodeStyle('n:any', null).state).toBe('normal')
  })

  it('着色映射', () => {
    expect(impactNodeStyle('svc:a', result).color).toBe('#ef4444')
    expect(impactNodeStyle('n:down', result).color).toBe('#f97316')
    expect(impactNodeStyle('n:up', result).color).toBe('#8b5cf6')
  })
})

describe('caseLink 链路高亮', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('caseLinkNodesOf 从全量边过滤三段链路', () => {
    const store = useKnowledgeStore()
    store.allNodes = [
      { id: 'case:e1', type: 'case', label: '案例', props: {} },
      { id: 'plant:金桥', type: 'plant', label: '金桥', props: {} },
      { id: 'pattern:secret_pipe', type: 'violation_pattern', label: '暗管', props: {} },
      { id: 'regulation:s39', type: 'regulation', label: '§39', props: {} },
      { id: 'plant:洗舱站', type: 'plant', label: '洗舱站', props: {} },  // 无关节键
    ] as any
    store.allEdges = [
      { id: 1, src: 'case:e1', dst: 'plant:金桥', type: 'involves', props: {} },
      { id: 2, src: 'case:e1', dst: 'pattern:secret_pipe', type: 'cites', props: {} },
      { id: 3, src: 'pattern:secret_pipe', dst: 'regulation:s39', type: 'indicates', props: {} },
      { id: 4, src: 'plant:金桥', dst: 'pattern:secret_pipe', type: 'monitors', props: {} },  // 无关边
    ] as any
    const nodes = caseLinkNodesOf('case:e1', store.allEdges)
    expect(nodes).not.toBeNull()
    expect(nodes!.has('case:e1')).toBe(true)
    expect(nodes!.has('plant:金桥')).toBe(true)
    expect(nodes!.has('pattern:secret_pipe')).toBe(true)
    expect(nodes!.has('regulation:s39')).toBe(true)       // 二跳法条
    expect(nodes!.has('plant:洗舱站')).toBe(false)
  })

  it('caseLinkNodesOf 无链路返回 null（只有自己）', () => {
    const nodes = caseLinkNodesOf('case:lonely', [
      { id: 9, src: 'a', dst: 'b', type: 'involves', props: {} },
    ] as any)
    expect(nodes).toBeNull()
  })

  it('highlightCase/clearCaseLink 状态机', () => {
    const store = useKnowledgeStore()
    store.allNodes = [{ id: 'case:e1', type: 'case', label: 'x', props: {} }] as any
    store.allEdges = [{ id: 1, src: 'case:e1', dst: 'p:a', type: 'involves', props: {} }] as any
    store.highlightCase('case:e1')
    expect(store.caseLinkNodes?.size).toBeGreaterThan(0)
    expect(store.caseLinkLabel).toBeTruthy()
    store.clearCaseLink()
    expect(store.caseLinkNodes).toBeNull()
    expect(store.caseLinkLabel).toBe('')
  })

  it('highlightCase 无链路时提示且不设状态', () => {
    const store = useKnowledgeStore()
    store.allEdges = [] as any
    store.highlightCase('case:none')
    expect(store.caseLinkNodes).toBeNull()
  })

  it('caseLink 与 impact 互斥（runImpact 清 caseLink）', async () => {
    const store = useKnowledgeStore()
    store.allNodes = [] as any; store.allEdges = [] as any
    store.caseLinkNodes = new Set(['x']) as any
    store._impactApi = vi.fn().mockResolvedValue({ node: {}, downstream: [], upstream: [] })
    await store.runImpact('svc:x')
    expect(store.caseLinkNodes).toBeNull()
  })

  it('highlightCase 清推演结果（双向互斥）+ setTab 清 caseLink', () => {
    const store = useKnowledgeStore()
    store.impactResult = { nodeId: 'x', node: null, downstream: [], upstream: [] } as any
    store.allEdges = [{ id: 1, src: 'case:e1', dst: 'p:a', type: 'involves', props: {} }] as any
    store.highlightCase('case:e1')
    expect(store.impactResult).toBeNull()
    expect(store.caseLinkNodes).not.toBeNull()
    store.setTab('domain')
    expect(store.caseLinkNodes).toBeNull()
  })
})
