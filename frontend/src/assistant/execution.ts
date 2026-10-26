import type { CandidateState } from '@/stores/assistant'
import type { AssistantExecutionResult } from './executor'
export async function runCandidate(candidate: CandidateState, execute: () => Promise<AssistantExecutionResult>) {
 if (!['prepared', 'failed'].includes(candidate.state)) return
 candidate.state = 'running'; candidate.receipt = undefined
 try {
 const result = await execute()
 candidate.receipt = result
 candidate.state = result.code === 'stale_context' ? 'stale' : result.success ? result.code === 'empty' ? 'empty' : 'succeeded' : 'failed'
 } catch (error) { candidate.state = 'failed'; candidate.receipt = { success: false, code: 'unexpected_error', message: error instanceof Error ? error.message : '页面操作失败，请重试' } }
}
