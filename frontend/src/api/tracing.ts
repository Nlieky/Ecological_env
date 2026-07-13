import api from './index'

export interface TracingDataSource {
  id: string
  name: string
  provider: string
  config: Record<string, any>
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface TraceSpan {
  traceID: string
  spanID: string
  operationName: string
  duration: number
  startTime: number
  tags: Record<string, string>
  logs: Array<{
    timestamp: number
    fields: Record<string, string>
  }>
  processID: string
  references?: Array<{
    refType: string
    traceID: string
    spanID: string
  }>
}

export interface TraceDetail {
  traceID: string
  spans: TraceSpan[]
  processes: Record<string, {
      serviceName: string
      tags?: Record<string, string>
    }>
}

export interface TraceSearchResult {
  traceID: string
  rootSpanName: string
  rootServiceName: string
  startTime: number
  duration: number
  spanCount: number
}

export const tracingApi = {
  // 获取链路追踪数据源列表
  getDataSources: () => {
    return api.get<any, TracingDataSource[]>('/observability/tracing/datasources')
  },

  // 创建链路追踪数据源
  createDataSource: (data: Omit<TracingDataSource, 'id' | 'created_at' | 'updated_at'>) => {
    return api.post('/observability/tracing/datasources', data)
  },

  // 更新链路追踪数据源
  updateDataSource: (id: string, data: Partial<TracingDataSource>) => {
    return api.put(`/observability/tracing/datasources/${id}`, data)
  },

  // 删除链路追踪数据源
  deleteDataSource: (id: string) => {
    return api.delete(`/observability/tracing/datasources/${id}`)
  },

  // 测试链路追踪数据源连接
  testDataSource: (id: string) => {
    return api.post(`/observability/tracing/datasources/${id}/test_connection`)
  },

  // 获取链路目录
  getCatalog: (params?: {
    service?: string
    operation?: string
    limit?: number
  }) => {
    return api.get<any, {
      services: Array<{
        name: string
        operations: string[]
      }>
    }>('/observability/tracing/catalog', { params })
  },

  // 搜索链路
  searchTraces: (data: {
    dataSourceId?: string
    service?: string
    operation?: string
    tags?: Record<string, string>
    startTimeMin?: string
    startTimeMax?: string
    durationMin?: number
    durationMax?: number
    limit?: number
  }) => {
    return api.post<any, TraceSearchResult[]>('/observability/tracing/search', data)
  },

  // 获取链路详情
  getTraceDetail: (traceId: string, params?: {
    dataSourceId?: string
  }) => {
    return api.get<any, TraceDetail>(`/observability/tracing/traces/${traceId}`, { params })
  }
}
