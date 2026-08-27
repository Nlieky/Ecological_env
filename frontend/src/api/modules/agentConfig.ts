// 智能体配置中心 API 模块（spec §3.1）
// 注意：client baseURL='/api'（响应拦截器已解包 response.data），后端路由挂在 /api/v1，
// 故此处路径以 /v1 开头（与 plants.ts 惯例一致）。
import api from '../client'

export interface AgentEntity {
  name: string; label: string; icon: string; dir: string
  identity_files: string[]
  skills: { name: string; has_skill: boolean }[]
}
export interface FileContent { path: string; content: string; size: number; mtime: string }
export interface FileHistoryItem { commit: string; date: string; author: string; message: string }
export interface ParamItem {
  key: string; value: string | number; default: string | number
  type: 'int' | 'str' | 'secret'; effect: 'immediate' | 'restart'
  reader: string; desc: string
}
export interface PlantConfig {
  hierarchy: Record<string, Record<string, string[]>>
  report_name_map: Record<string, string>
  plant_configs: Record<string, Record<string, unknown>>
  plant_aliases: Record<string, string>
}

/** 通用响应包裹 */
export interface ApiResponse<T> { success: boolean; data: T }

export const agentConfigService = {
  /** 实体列表（主智能体+4子智能体） */
  entities: () => api.get<unknown, ApiResponse<AgentEntity[]>>('/v1/agents/config/entities'),

  /** 读身份文件内容 */
  readFile: (entity: string, file: string) =>
    api.get<unknown, ApiResponse<FileContent>>('/v1/agents/config/files', { params: { entity, file } }),

  /** 保存身份文件（git 快照） */
  saveFile: (body: { entity: string; file: string; content: string; message?: string }) =>
    api.put<unknown, ApiResponse<unknown>>('/v1/agents/config/files', body),

  /** 文件历史（git log） */
  fileHistory: (entity: string, file: string, limit = 20) =>
    api.get<unknown, ApiResponse<FileHistoryItem[]>>('/v1/agents/config/files/history',
      { params: { entity, file, limit } }),

  /** 回滚到指定 commit */
  revertFile: (body: { entity: string; file: string; commit: string }) =>
    api.post<unknown, ApiResponse<unknown>>('/v1/agents/config/files/revert', body),

  /** 厂区配置（yaml） */
  getPlants: () => api.get<unknown, ApiResponse<PlantConfig>>('/v1/agents/config/plants'),

  /** 校验厂区配置（不落盘） */
  validatePlants: (body: Partial<PlantConfig>) =>
    api.post<unknown, { success: boolean; errors: string[] }>('/v1/agents/config/plants/validate', body),

  /** 保存厂区配置 */
  savePlants: (body: Partial<PlantConfig>) =>
    api.put<unknown, ApiResponse<unknown>>('/v1/agents/config/plants', body),

  /** 运行参数列表（secret 已脱敏） */
  getParams: () => api.get<unknown, ApiResponse<ParamItem[]>>('/v1/agents/config/params'),

  /** 批量保存参数；secret 留空=不改 */
  saveParams: (params: Record<string, string | number>) =>
    api.put<unknown, { success: boolean; restart_needed: boolean }>('/v1/agents/config/params', { params }),

  /** LLM 连通性测试（空字段=用当前生效配置） */
  llmTest: (body: { base_url?: string; model?: string; api_key?: string }) =>
    api.post<unknown, { ok: boolean; latency_ms?: number; error: string | null }>('/v1/agents/config/llm/test', body),

  /** agent 服务状态 */
  serviceStatus: () => api.get<unknown, ApiResponse<unknown>>('/v1/agents/config/service/status'),

  /** 重启 agent 服务（confirm=true） */
  serviceRestart: () =>
    api.post<unknown, { success?: boolean; ok?: boolean; [k: string]: unknown }>('/v1/agents/config/service/restart', { confirm: true }),
}
