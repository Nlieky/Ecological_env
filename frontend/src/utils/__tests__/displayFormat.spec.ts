import { expect, it } from 'vitest'
import { formatValue, formatDateTime, formatDuration, formatRisk, formatDataContext, formatAgentStatus, formatServiceStatus } from '../displayFormat'

it('formats missing values, Shanghai timestamps and millisecond duration', () => {
  expect(formatValue(null)).toBe('—'); expect(formatValue(0)).toBe('0')
  expect(formatDateTime('2026-01-01T00:00:00Z')).toBe('2026-01-01 08:00:00')
  expect(formatDateTime('invalid')).toBe('—')
  expect(formatDuration(128433)).toBe('2分08秒')
  expect(formatDuration(500)).toBe('500ms')
})
it('keeps risk unconfirmed and unknown operational states honest', () => {
  expect(formatRisk('violation')).toBe('违规嫌疑')
  expect(formatRisk('violation', true)).toBe('已确认违规')
  expect(formatAgentStatus('running')).toBe('运行中')
  expect(formatAgentStatus('queued')).toBe('排队中')
  expect(formatAgentStatus('cancelled')).toBe('接收已停止')
  expect(['up', 'down', 'initializing', 'unconfigured'].map(formatServiceStatus)).toEqual(['运行正常', '服务不可达', '初始化中', '尚未配置'])
  expect(formatDataContext({ origin: 'imported', mode: 'simulation' })).toContain('真实导入 · 模拟回放')
  expect(formatDataContext({ origin: 'api', mode: 'live' })).toContain('实时接口')
  expect(formatServiceStatus('unknown')).toBe('状态未核验')
  expect(formatDataContext({ origin: 'real', mode: 'live', freshness: 'stale' })).toContain('数据已过期')
})
