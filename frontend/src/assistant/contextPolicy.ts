import { capabilityDescriptor, type AssistantAction } from './capabilities'
type Context = Record<string, unknown>
export const contextValue = (context: Context, field: string): unknown => field.split('.').reduce<unknown>((value, key) => value && typeof value === 'object' ? (value as Context)[key] : undefined, context)
const labels: Record<string, string> = { route: '页面', pageId: '页面', objectId: '对象', plant: '厂站', source: '数据来源', range: '时间窗口', indicator: '指标', 'filters.side': '进出水侧别' }
export function contextPolicy(action: AssistantAction, captured: Context | null, current: Context | null): string | null {
 const descriptor = capabilityDescriptor(action.capability)
 if (!descriptor) return '能力未开放'
 if (descriptor.invalidation.mode === 'destination') return null
 if (!captured || !current) return '来源页面已变化，请重新准备操作'
 const readiness = descriptor.readiness
 if ((captured.route === descriptor.target_path || ['window', 'proposal'].includes(descriptor.invalidation.mode)) && readiness.status.length && (!(readiness.status as string[]).includes(String(captured.status)) || !(readiness.status as string[]).includes(String(current.status)))) return '来源数据尚未就绪，请重新准备操作'
 for (const context of [captured, current]) {
 if (readiness.required_context.some(field => !contextValue(context, field))) return '来源上下文不完整，请重新准备操作'
 if (readiness.range_requires_bounds) { const range = context.range as { start?: unknown; end?: unknown } | null; if (!range || typeof range !== 'object' || !range.start || !range.end) return '来源时间窗口缺少明确起止时间，请重新准备操作' }
 }
 for (const field of descriptor.invalidation.fields) {
 const overridden = Object.entries(descriptor.inheritance).some(([parameter, inherited]) => inherited === field && Object.prototype.hasOwnProperty.call(action.parameters, parameter) && (!action.parameter_sources || action.parameter_sources[parameter] === 'explicit'))
 if (overridden && (descriptor.invalidation.mode === 'relative' || (field !== 'plant' && descriptor.invalidation.mode === 'window'))) continue
 if (JSON.stringify(contextValue(captured, field)) !== JSON.stringify(contextValue(current, field))) return `${labels[field] || field}已变化，请基于当前页面重新准备操作`
 }
 return null
}
