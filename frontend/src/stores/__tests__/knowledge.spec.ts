// frontend/src/stores/__tests__/knowledge.spec.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { toEChartsSeries, NODE_META, computeVisibleTypes, useKnowledgeStore } from '@/stores/knowledge'

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

  it('节点映射为 data，id/name/category 齐全；category 带图例配色', () => {
    const s = toEChartsSeries(nodes, edges, ['plant', 'indicator', 'violation_pattern'])
    expect(s.data).toHaveLength(3)
    expect(s.data[0]).toMatchObject({ id: 'plant:jinqiao', name: '金桥一期', category: 0 })
    expect(s.categories).toHaveLength(3)
    // 图例(legend)从 category.itemStyle 取色——必须与节点颜色一致
    expect(s.categories[0]).toMatchObject({ name: '厂区', itemStyle: { color: '#22c55e' } })
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

describe('computeVisibleTypes（hidden 反向集合）', () => {
  it('空 hidden = 全选该 tab 预设', () => {
    expect(computeVisibleTypes('domain', [])).toEqual(
      ['plant', 'indicator', 'violation_pattern', 'operator', 'regulation', 'case'])
    expect(computeVisibleTypes('topology', [])).toEqual(['agent', 'service'])
  })

  it('hidden 排除对应类型（取消勾选即隐藏）', () => {
    expect(computeVisibleTypes('domain', ['plant', 'case'])).toEqual(
      ['indicator', 'violation_pattern', 'operator', 'regulation'])
  })

  it('hidden 覆盖全部类型时返回空数组（不回退全选）', () => {
    expect(computeVisibleTypes('topology', ['agent', 'service'])).toEqual([])
  })
})

describe('knowledge store 图例反选（hiddenTypes）', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('初始 hidden 空 → visibleTypes 为当前 tab 全集', () => {
    const store = useKnowledgeStore()
    expect(store.hiddenTypes).toEqual([])
    expect(store.visibleTypes).toHaveLength(6) // domain 6 类
  })

  it('toggleType 双向：取消勾选=加入 hidden（隐藏），重新勾选=移出（恢复）', () => {
    const store = useKnowledgeStore()
    store.toggleType('plant')
    expect(store.hiddenTypes).toEqual(['plant'])
    expect(store.visibleTypes).not.toContain('plant')
    store.toggleType('plant')
    expect(store.hiddenTypes).toEqual([])
    expect(store.visibleTypes).toContain('plant')
  })

  it('setTab 切换 tab 并重置 hidden', () => {
    const store = useKnowledgeStore()
    store.toggleType('plant')
    store.setTab('topology')
    expect(store.activeTab).toBe('topology')
    expect(store.hiddenTypes).toEqual([])
    expect(store.visibleTypes).toEqual(['agent', 'service'])
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
