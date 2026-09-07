// frontend/src/stores/__tests__/knowledge.spec.ts
import { describe, it, expect } from 'vitest'
import { toEChartsSeries, NODE_META } from '@/stores/knowledge'

describe('toEChartsSeries', () => {
  const nodes = [
    { id: 'plant:jinqiao', type: 'plant', label: '金桥一期', props: {} },
    { id: 'indicator:COD', type: 'indicator', label: 'COD', props: {} },
    { id: 'pattern:bottle', type: 'violation_pattern', label: '插瓶干扰', props: {} },
    { id: 'agent:master', type: 'agent', label: '主智能体', props: {} },
  ]
  const edges = [
    { id: 1, src: 'plant:jinqiao', dst: 'indicator:COD', type: 'monitors', props: {} },
    { id: 2, src: 'indicator:COD', dst: 'pattern:bottle', type: 'monitors', props: {} },
    { id: 3, src: 'agent:master', dst: 'pattern:bottle', type: 'employs', props: {} },
  ]

  it('节点映射为 data，id/name/category 齐全', () => {
    const s = toEChartsSeries(nodes, edges, ['plant', 'indicator', 'violation_pattern'])
    expect(s.data).toHaveLength(3)
    expect(s.data[0]).toMatchObject({ id: 'plant:jinqiao', name: '金桥一期', category: 0 })
    expect(s.categories).toHaveLength(3)
  })

  it('边仅当两端类型都在可见集合内才保留', () => {
    const s = toEChartsSeries(nodes, edges, ['plant', 'indicator'])
    expect(s.links).toHaveLength(1) // 两条 monitors 端点都可见; employs 的 agent 不可见
    expect(s.links[0]).toMatchObject({ source: 'plant:jinqiao', target: 'indicator:COD' })
  })

  it('空图返回空数组', () => {
    const s = toEChartsSeries([], [], ['plant'])
    expect(s.data).toHaveLength(0)
    expect(s.links).toHaveLength(0)
  })
})

describe('NODE_META', () => {
  it('8 类节点齐备且 tab 归属二分', () => {
    const types = Object.keys(NODE_META)
    expect(types).toEqual(expect.arrayContaining([
      'plant', 'indicator', 'violation_pattern', 'operator',
      'regulation', 'case', 'agent', 'service',
    ]))
    for (const meta of Object.values(NODE_META)) {
      expect(['domain', 'topology']).toContain(meta.tab)
    }
  })
})
