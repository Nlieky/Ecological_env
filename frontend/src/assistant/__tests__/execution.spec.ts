import { expect, it, vi } from 'vitest'
import { runCandidate } from '../execution'
it('ignores duplicate clicks and replaces its receipt without polluting conversation', async () => {
 let finish!: (value: any) => void
 const execute = vi.fn(() => new Promise<any>(resolve => { finish = resolve }))
 const candidate = { state: 'prepared' as const }
 const first = runCandidate(candidate, execute); await runCandidate(candidate, execute)
 expect(execute).toHaveBeenCalledTimes(1)
 finish({ success: true, message: 'done', details: { count: 2 } }); await first
 expect(candidate).toMatchObject({ state: 'succeeded', receipt: { message: 'done' } })
 await runCandidate(candidate, execute); expect(execute).toHaveBeenCalledTimes(1)
})
it('turns unexpected failures into a retryable receipt', async () => {
 const candidate = { state: 'prepared' as const }
 await runCandidate(candidate, async () => { throw new Error('unexpected') })
 expect(candidate).toMatchObject({ state: 'failed', receipt: { success: false, message: 'unexpected' } })
})
