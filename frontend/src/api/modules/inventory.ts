import request from '../request'

/**
 * 库存分析驾驶舱 — 数据接口
 * 当前返回 null 表示后端尚未提供，前端使用内置样本数据。
 */
export const getInventoryData = async (): Promise<Record<string, unknown> | null> => {
  try {
    const data = await request.get<Record<string, unknown>>('/inventory/all')
    return data
  } catch {
    return null
  }
}

/** 健康检查 */
export const getHealth = () => request.get<{ msg: string }>('/health')
