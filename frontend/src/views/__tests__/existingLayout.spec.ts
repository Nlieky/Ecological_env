import { describe, expect, it } from 'vitest'
import chat from '../AIOpsChatView.vue?raw'
import audit from '../AgentAuditView.vue?raw'
import logs from '../LogsView.vue?raw'
import trace from '../TraceView.vue?raw'
import plants from '../PlantsConfigView.vue?raw'
const sources: Record<string, string> = { AIOpsChatView: chat, AgentAuditView: audit, LogsView: logs, TraceView: trace, PlantsConfigView: plants }
const source = (name: string) => sources[name]
describe('existing operational page containment', () => {
  it.each(['AIOpsChatView', 'AgentAuditView', 'LogsView', 'TraceView', 'PlantsConfigView'])('%s uses the shared full-height shell without viewport arithmetic', name => {
    expect(source(name)).toContain('<PageShell')
    expect(source(name)).not.toContain('calc(100vh')
  })
  it('keeps log refresh data only for its matching conditions', () => {
    expect(source('LogsView')).toContain('loadedKey')
    expect(source('LogsView')).toContain('preserve-content')
  })
  it('does not advertise a hard-coded chat model', () => {
    expect(source('AIOpsChatView')).not.toContain('ctgu-vlm')
  })
})
