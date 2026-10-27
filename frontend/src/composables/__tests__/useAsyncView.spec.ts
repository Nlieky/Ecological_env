import { describe, expect, it } from 'vitest'
import { useAsyncView } from '../useAsyncView'

describe('useAsyncView', () => {
  it('ignores late results and disposed requests', async () => {
    const resolvers: ((value: number) => void)[] = []
    const view = useAsyncView(() => new Promise<number>(resolve => resolvers.push(resolve)))
    const first = view.run(); const second = view.run()
    resolvers[1]!(2); await second
    resolvers[0]!(1); await first
    expect(view.data.value).toBe(2)
    const third = view.run(); view.dispose(); resolvers[2]!(3); await third
    expect(view.data.value).toBe(2)
  })
  it('retains old data on refresh failure and retries safely', async () => {
    let fail = false
    const view = useAsyncView(async () => { if (fail) throw new Error('secret stack token'); return [1] })
    await view.run(); fail = true
    const refresh = view.refresh()
    expect(view.state.value).toBe('refreshing')
    await refresh
    expect(view.data.value).toEqual([1])
    expect(view.state.value).toBe('error')
    expect(view.error.value).not.toContain('secret')
    fail = false; await view.retry()
    expect(view.state.value).toBe('ready')
  })
  it('distinguishes empty results and initial failure', async () => {
    const empty = useAsyncView(async () => [], { isEmpty: value => value.length === 0 })
    await empty.run(); expect(empty.state.value).toBe('empty')
    const failed = useAsyncView(async () => { throw 'sensitive' })
    await failed.run(); expect(failed.state.value).toBe('error')
    expect(failed.data.value).toBeUndefined()
  })
})
