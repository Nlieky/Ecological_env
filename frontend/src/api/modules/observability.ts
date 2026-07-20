import api from '../client'
import type { TracingDataSource, DataSourceInput, TestConnectionResult } from '../types/api.types'

// 注意：tracing 数据源端点返回非 envelope（直接数组/对象）；client 拦截器已返回 body。
export const observabilityService = {
  listDatasources: () => api.get<unknown, TracingDataSource[]>('/observability/tracing/datasources'),
  createDatasource: (data: DataSourceInput) =>
    api.post<unknown, TracingDataSource>('/observability/tracing/datasources', data),
  updateDatasource: (id: string, data: Partial<DataSourceInput>) =>
    api.put<unknown, TracingDataSource>(`/observability/tracing/datasources/${id}`, data),
  deleteDatasource: (id: string) =>
    api.delete<unknown, { message: string }>(`/observability/tracing/datasources/${id}`),
  testConnection: (id: string) =>
    api.post<unknown, TestConnectionResult>(`/observability/tracing/datasources/${id}/test_connection`),
}
