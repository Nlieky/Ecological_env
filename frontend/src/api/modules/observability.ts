import api from '../client'
import type {
  TracingDataSource, DataSourceInput, TestConnectionResult,
  CatalogResponse, TraceSearchResult, TraceDetail,
} from '../types/api.types'

// 注意：tracing 端点返回非 envelope（直接数组/对象）；client 拦截器已返回 body。
export const observabilityService = {
  // 数据源 CRUD
  listDatasources: () => api.get<unknown, TracingDataSource[]>('/observability/tracing/datasources'),
  createDatasource: (data: DataSourceInput) =>
    api.post<unknown, TracingDataSource>('/observability/tracing/datasources', data),
  updateDatasource: (id: string, data: Partial<DataSourceInput>) =>
    api.put<unknown, TracingDataSource>(`/observability/tracing/datasources/${id}`, data),
  deleteDatasource: (id: string) =>
    api.delete<unknown, { message: string }>(`/observability/tracing/datasources/${id}`),
  testConnection: (id: string) =>
    api.post<unknown, TestConnectionResult>(`/observability/tracing/datasources/${id}/test_connection`),
  // 链路目录 / 搜索 / 详情
  catalog: (params: { service?: string; operation?: string; limit?: number } = {}) =>
    api.get<unknown, CatalogResponse>('/observability/tracing/catalog', { params }),
  search: (data: { service?: string; operation?: string; durationMin?: number; limit?: number }) =>
    api.post<unknown, TraceSearchResult[]>('/observability/tracing/search', data),
  trace: (id: string) => api.get<unknown, TraceDetail>(`/observability/tracing/traces/${id}`),
}
