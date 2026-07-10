// ============================================
// API 通用类型
// ============================================

/** 后端统一响应格式 */
export interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}

/** API 错误 */
export class ApiError extends Error {
  code: number
  constructor(code: number, message: string) {
    super(message)
    this.code = code
    this.name = 'ApiError'
  }
}
