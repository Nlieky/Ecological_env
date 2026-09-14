// frontend/src/stores/__tests__/knowledge.impact.spec.ts
// vitest 环境是 node（无 DOM），ElMessage 需 document——mock 掉（runImpact 失败分支用到）
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useKnowledgeStore, impactNodeStyle } from '@/stores/knowledge'

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
