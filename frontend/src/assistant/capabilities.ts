import contract from './contract.generated.json'
export interface AssistantAction { id?: string; capability: string; parameters: Record<string, unknown>; label?: string; contract_version?: string; parameter_sources?: Record<string, string> }
export const CONTRACT_VERSION = contract.contract_version
export const capabilityDescriptor = (id: string) => contract.capabilities.find(item => item.id === id)
export const ASSISTANT_PAGES = { dashboard: '/dashboard', metrics: '/metrics', events: '/events', audit: '/agents/audit', graph: '/agents/knowledge', logs: '/logs', config: '/agents/config', chat: '/chat' } as const
export const LOG_MODULES = capabilityDescriptor('logs.filter')!.parameters.module as string[]
export const STRATEGY_FIELDS = Object.keys(capabilityDescriptor('strategy.draft')!.parameters)
export const ASSISTANT_CAPABILITIES = contract.capabilities.map(item => item.id)
export function validateAssistantAction(action: AssistantAction): { success: boolean; message: string } {
 const descriptor = capabilityDescriptor(action?.capability), params = action?.parameters
 if (action?.contract_version && action.contract_version !== CONTRACT_VERSION) return { success: false, message: '操作协议已变化，请重新准备操作' }
 if (!descriptor || !params || typeof params !== 'object' || Array.isArray(params)) return { success: false, message: '未注册能力或参数无效' }
 const schema = descriptor.parameters as Record<string, unknown>
 if (Object.keys(params).length < descriptor.minimum_parameters || descriptor.required.some(key => !(key in params)) || Object.entries(params).some(([key, value]) => {
 const rule = schema[key]
 return !Object.prototype.hasOwnProperty.call(schema, key) || (Array.isArray(rule) ? !rule.includes(value) : rule === 'bool' ? typeof value !== 'boolean' : typeof value !== 'string' || !value.trim() || value.length > (key === 'reason' ? 1000 : 256))
 })) return { success: false, message: '参数超出已注册字段或取值范围，或缺少明确目标' }
 return { success: true, message: '参数已验证' }
}
