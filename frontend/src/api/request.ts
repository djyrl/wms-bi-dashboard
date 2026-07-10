import axios from 'axios'
import type { AxiosInstance, AxiosResponse, AxiosRequestConfig } from 'axios'
import { ApiError } from '@/types/api'

/** 创建 Axios 实例 */
const instance: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ========== 请求拦截器 ==========
instance.interceptors.request.use(
  (config) => {
    // TODO: 注入 token
    // const token = localStorage.getItem('token')
    // if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error),
)

// ========== 响应拦截器 ==========
instance.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response
    // 后端返回格式: { code: 0, data: {...} }
    if (data.code === 0) {
      return data.data
    }
    throw new ApiError(data.code, data.message || '请求失败')
  },
  (error) => {
    if (error instanceof ApiError) throw error
    // 网络错误
    const message =
      error.response?.data?.message || error.message || '网络请求失败'
    throw new ApiError(-1, message)
  },
)

/**
 * 包装 Axios 实例，使得请求方法直接返回 T 而非 AxiosResponse<T>。
 * 因为响应拦截器已经解包了外层的 { code, data } 信封。
 */
const request = {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as Promise<T>
  },
  post<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    return instance.post(url, data, config) as Promise<T>
  },
  put<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    return instance.put(url, data, config) as Promise<T>
  },
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config) as Promise<T>
  },
}

export default request
