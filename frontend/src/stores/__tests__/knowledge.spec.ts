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
    // 图例(legend)从 category.itemStyle 取色——必须与节点颜色一致（2026-09-08 降饱和重配）
    expect(s.categories[0]).toMatchObject({ name: '厂区', itemStyle: { color: '#3b82f6' } })
    // 度数编码：bottle 连 2 条可见边(COD→bottle, agent→bottle 但 agent 不可见→1 条)，
    // hub 判定与 degree 字段存在
    const bottle = s.data.find(d => d.id === 'pattern:bottle')
    expect(bottle?.degree).toBe(1)
    expect(typeof bottle?.symbolSize).toBe('number')
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

  it('agent+operator 同可见时 employs 边保留（topology tab 边可见性，spec L66）', () => {
    const s = toEChartsSeries(nodes, edges, ['agent', 'operator'])
    // employs: agent:master → pattern:bottle 是违规模式端点，不含 pattern 时仍滤掉
    expect(s.links).toHaveLength(0)
    // 造一条 agent → operator 的 employs 边：两端都可见才保留
    const edges2 = [
      { id: 4, src: 'agent:master', dst: 'operator:iforest', type: 'employs', props: {} },
    ]
    const nodes2 = [
      { id: 'agent:master', type: 'agent', label: '主智能体', props: {} },
      { id: 'operator:iforest', type: 'operator', label: '孤立森林', props: {} },
    ]
    const s2 = toEChartsSeries(nodes2, edges2, ['agent', 'operator'])
    expect(s2.data).toHaveLength(2)
    expect(s2.links).toHaveLength(1)
    expect(s2.links[0]).toMatchObject({ source: 'agent:master', target: 'operator:iforest', value: 'employs' })
    // operator 在 topology tab 是核心成员（度数同为 1 时比 domain 侧大 6px）
    const agent = s2.data.find(d => d.id === 'agent:master')
    const op = s2.data.find(d => d.id === 'operator:iforest')
    expect((op?.symbolSize ?? 0)).toBeGreaterThan((agent?.symbolSize ?? 0) - 1)
  })
})

describe('computeVisibleTypes（hidden 反向集合）', () => {
  it('空 hidden = 全选该 tab 预设', () => {
    expect(computeVisibleTypes('domain', [])).toEqual(
      ['plant', 'indicator', 'violation_pattern', 'operator', 'regulation', 'case'])
    // 顺序=NODE_META 键序：operator 在 agent/service 前
    expect(computeVisibleTypes('topology', [])).toEqual(['operator', 'agent', 'service'])
  })

  it('operator 双 tab 归属（spec L66）——domain 与 topology 的可见集都含 operator', () => {
    expect(computeVisibleTypes('domain', [])).toContain('operator')
    expect(computeVisibleTypes('topology', [])).toContain('operator')
  })

  it('hidden 排除对应类型（取消勾选即隐藏）', () => {
    expect(computeVisibleTypes('domain', ['plant', 'case'])).toEqual(
      ['indicator', 'violation_pattern', 'operator', 'regulation'])
  })

  it('hidden 覆盖全部类型时返回空数组（不回退全选）', () => {
    expect(computeVisibleTypes('topology', ['agent', 'service', 'operator'])).toEqual([])
    // operator 属 topology 预设：只 hidden agent/service 时仍剩 operator
    expect(computeVisibleTypes('topology', ['agent', 'service'])).toEqual(['operator'])
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
    expect(store.visibleTypes).toEqual(['operator', 'agent', 'service'])
  })
})

describe('NODE_META', () => {
  it('8 类节点齐备且 tab 归属为数组（operator 双归属）', () => {
    const types = Object.keys(NODE_META)
    expect(types).toEqual(expect.arrayContaining([
      'plant', 'indicator', 'violation_pattern', 'operator',
      'regulation', 'case', 'agent', 'service',
    ]))
    for (const meta of Object.values(NODE_META)) {
      expect(Array.isArray(meta.tab)).toBe(true)
      for (const t of meta.tab) expect(['domain', 'topology']).toContain(t)
    }
    expect(NODE_META.operator.tab).toEqual(['domain', 'topology'])
  })
})
