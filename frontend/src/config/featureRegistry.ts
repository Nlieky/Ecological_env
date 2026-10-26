import type { RouteMeta } from 'vue-router'

export type FeatureStatus = 'stable' | 'experimental' | 'hidden'

export interface FeatureDefinition {
  path: string
  title: string
  group: string
  status: FeatureStatus
  purpose?: string
  dependency?: string
}

export interface NavigationGroup {
  title: string
  items: FeatureDefinition[]
}

export const FEATURES = [
  { path: '/chat', title: 'AI助手', group: '智能助手', status: 'stable' },
  { path: '/agents/audit', title: '智能体审计', group: '智能助手', status: 'stable' },
  { path: '/agents/knowledge', title: '知识图谱', group: '智能助手', status: 'stable' },
  { path: '/agents/config', title: '智能体配置', group: '智能助手', status: 'stable' },
  { path: '/dashboard', title: '监测大屏', group: '监测分析', status: 'stable' },
  { path: '/metrics', title: '指标查询', group: '监测分析', status: 'stable' },
  { path: '/plants/config', title: '厂区配置', group: '监测分析', status: 'stable' },
  { path: '/events', title: '事件中心', group: '事件处置', status: 'stable' },
  { path: '/logs', title: '日志中心', group: '系统运维', status: 'stable' },
  { path: '/tracing', title: '链路追踪', group: '实验功能', status: 'experimental', purpose: '查看系统调用链与服务耗时，辅助系统故障排查。', dependency: 'Jaeger 等追踪服务及系统追踪数据接入。' },
  { path: '/datasources', title: '可观测性数据源', group: '实验功能', status: 'experimental', purpose: '配置 Jaeger 等系统追踪数据源，服务于系统可观测性。', dependency: '可访问的 Jaeger 等服务及对应连接配置。' },
  { path: '/grafana', title: 'Grafana大屏', group: '实验功能', status: 'experimental', purpose: '用于未来系统监测，不承担当前废水业务数据显示。', dependency: 'Grafana、系统监测指标源与相应仪表盘配置。' },
  { path: '/alerts', title: '告警中心', group: '实验功能', status: 'experimental', purpose: '探索系统告警规则与通知管理。', dependency: '系统告警数据接入、规则和通知服务。' },
  { path: '/event-sources', title: '事件源', group: '实验功能', status: 'experimental', purpose: '探索事件来源与事件接入配置。', dependency: '事件来源适配器及接入配置。' },
  { path: '/settings', title: '系统设置', group: '实验功能', status: 'experimental', purpose: '预留通用系统设置入口。', dependency: '对应系统设置服务与配置协议。' },
  { path: '/experimental', title: '实验功能', group: '实验功能', status: 'hidden' },
] as const satisfies readonly FeatureDefinition[]

export type FeaturePath = (typeof FEATURES)[number]['path']

export interface FeatureRouteMeta extends RouteMeta {
  title: string
  group: string
  featureStatus: FeatureStatus
}

export function featureByPath(path: string): FeatureDefinition | undefined {
  const normalizedPath = path.replace(/\/+$/, '') || '/'
  return FEATURES.find(feature => feature.path === normalizedPath)
}

export function stableNavigation(): NavigationGroup[] {
  return FEATURES.filter(feature => feature.status === 'stable').reduce<NavigationGroup[]>((groups, feature) => {
    let group = groups.find(candidate => candidate.title === feature.group)
    if (!group) {
      group = { title: feature.group, items: [] }
      groups.push(group)
    }
    group.items.push(feature)
    return groups
  }, [])
}

export function experimentalFeatures(): FeatureDefinition[] {
  return FEATURES.filter(feature => feature.status === 'experimental')
}

export function featureMeta(path: FeaturePath): FeatureRouteMeta {
  const feature = featureByPath(path)
  if (!feature) throw new Error(`Unknown feature path: ${path}`)
  return { title: feature.title, group: feature.group, featureStatus: feature.status }
}
