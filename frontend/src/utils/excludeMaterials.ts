/**
 * 前台展示过滤 — 排除指定物资，仅影响显示，不影响后台计算（库存金额等）。
 */

/** 不展示的物资编码 */
export const EXCLUDED_MATERIAL_CODES = new Set([
  '10212957', // 电动机 315kW — 前台屏蔽，后台库存保留
])

/** 过滤掉排除的物资 */
export function filterExcluded<T extends { material_code?: string }>(items: T[]): T[] {
  return items.filter(item => !item.material_code || !EXCLUDED_MATERIAL_CODES.has(item.material_code))
}
