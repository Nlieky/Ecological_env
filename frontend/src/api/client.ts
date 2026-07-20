import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5min,适配 AI 查询
})

api.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    const detail: any = error.response?.data as any
    const message = detail?.detail?.message || detail?.detail || detail?.error?.message || error.message || '请求失败'
    if (!error.config?.headers?.['X-Skip-Error']) {
      ElMessage.error(typeof message === 'string' ? message : '请求失败')
    }
    return Promise.reject(error)
  },
)

// 静默请求(不弹错)的便捷开关:传 { headers: { 'X-Skip-Error': '1' } }
export const SILENT = { headers: { 'X-Skip-Error': '1' } } as const

export default api
