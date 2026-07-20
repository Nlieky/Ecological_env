import { describe, it, expect } from 'vitest'
import { classifyTrend, sparklinePoints } from '../useSparkline'

describe('classifyTrend', () => {
  it('上升序列 => up', () => expect(classifyTrend([1, 2, 3, 4, 5])).toBe('up'))
  it('下降序列 => down', () => expect(classifyTrend([5, 4, 3, 2, 1])).toBe('down'))
  it('高频震荡 => volatile', () => expect(classifyTrend([1, 9, 1, 9, 1, 9])).toBe('volatile'))
  it('恒定 => flat', () => expect(classifyTrend([7, 7, 7, 7])).toBe('flat'))
  it('空/单点 => flat', () => {
    expect(classifyTrend([])).toBe('flat')
    expect(classifyTrend([3])).toBe('flat')
  })
})

describe('sparklinePoints', () => {
  it('返回 viewBox 内的 "x,y x,y" 串,首点贴左、末点贴右', () => {
    const pts = sparklinePoints([1, 2, 3], 100, 30).split(' ')
    expect(pts).toHaveLength(3)
    const [x0] = pts[0].split(',').map(Number)
    const [x2] = pts[2].split(',').map(Number)
    expect(x0).toBe(0)
    expect(x2).toBe(100)
  })
  it('所有 y 落在 [0, height]', () => {
    const ys = sparklinePoints([3, 1, 4, 1, 5], 100, 30).split(' ').map(p => Number(p.split(',')[1]))
    expect(Math.min(...ys)).toBeGreaterThanOrEqual(0)
    expect(Math.max(...ys)).toBeLessThanOrEqual(30)
  })
})
