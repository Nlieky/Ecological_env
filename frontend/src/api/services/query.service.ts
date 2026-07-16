import api from '../client'
import type { QueryRequest, QueryResponse } from '../types/api.types'

export class QueryService {
  private readonly basePath = '/query'

  /**
   * 执行自然语言查询
   */
  async executeQuery(request: QueryRequest): Promise<QueryResponse> {
    return api.post(this.basePath, request)
  }

  /**
   * 获取智能体能力说明
   */
  async getCapabilities(): Promise<any> {
    return api.get(`${this.basePath}/capabilities`)
  }
}

export const queryService = new QueryService()
