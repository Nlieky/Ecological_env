import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { usePolling } from '../usePolling'

describe('usePolling', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('按间隔调用回调', () => {
    const fn = vi.fn()
    const { start, stop } = usePolling(fn, 1000)
    start()
    expect(fn).toHaveBeenCalledTimes(1) // 启动即调一次
    vi.advanceTimersByTime(3000)
    expect(fn).toHaveBeenCalledTimes(4)
    stop()
  })

  it('stop 后不再调用', () => {
    const fn = vi.fn()
    const { start, stop } = usePolling(fn, 1000)
    start()
    stop()
    vi.advanceTimersByTime(5000)
    expect(fn).toHaveBeenCalledTimes(1)
  })
})
