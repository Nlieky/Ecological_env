import { expect, it, vi } from 'vitest'
import api from '@/api/client'
import { logsService } from '../logs'
vi.mock('@/api/client', () => ({ default: { get: vi.fn() } }))
it('encodes session identifiers as one trace URL segment', () => {
  logsService.trace('A/B?#')
  expect(api.get).toHaveBeenCalledWith('/logs/trace/A%2FB%3F%23')
})
