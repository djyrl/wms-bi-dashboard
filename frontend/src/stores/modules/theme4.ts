import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getTopUnclaimedAmount, getOptimizeSuggest } from '@/api/modules/theme4'
import type { TopUnclaimedItem } from '@/api/modules/theme4'
import type {
  SluggishItem,
  OverstockItem,
  CleanupItem,
  OptimizeSuggestItem,
  KpiCardData,
} from '@/types/inventory'

// ═══ 示例数据（来自 temp/theme4-top-list.html 原型） ═══

const SAMPLE_SLUGGISH: SluggishItem[] = [
  { code: 'MAT-2023-0892', name: '高压开关柜配件', age: 385, amount: 186, quantity: 12, unit: '台', project: 'C-检修', projectName: 'C-检修', buyer: '王建华', suggest: '报废处置', level: 'red' },
  { code: 'MAT-2024-0156', name: '特种阀门DN200', age: 312, amount: 152, quantity: 8, unit: '个', project: 'A-扩建', projectName: 'A-扩建', buyer: '张建国', suggest: '折价转让', level: 'red' },
  { code: 'MAT-2024-0234', name: '防爆电缆YJV22', age: 298, amount: 138, quantity: 350, unit: '米', project: 'G-研发', projectName: 'G-研发', buyer: '杨海峰', suggest: '项目间调拨', level: 'amber' },
  { code: 'MAT-2024-0412', name: '进口轴承SKF', age: 265, amount: 95, quantity: 24, unit: '个', project: 'B-技改', projectName: 'B-技改', buyer: '李明辉', suggest: '降级使用', level: 'amber' },
  { code: 'MAT-2024-0567', name: '不锈钢管件Φ108', age: 242, amount: 88, quantity: 45, unit: '个', project: 'C-检修', projectName: 'C-检修', buyer: '王建华', suggest: '折价转让', level: 'amber' },
  { code: 'MAT-2024-0721', name: 'PLC控制模块', age: 228, amount: 76, quantity: 6, unit: '台', project: 'D-新建', projectName: 'D-新建', buyer: '赵志强', suggest: '退回供应商', level: 'amber' },
  { code: 'MAT-2024-0892', name: '仪表变送器', age: 205, amount: 65, quantity: 18, unit: '台', project: 'E-运维', projectName: 'E-运维', buyer: '陈伟明', suggest: '降级使用', level: 'amber' },
  { code: 'MAT-2024-1034', name: '密封垫片组件', age: 185, amount: 52, quantity: 60, unit: '套', project: 'B-技改', projectName: 'B-技改', buyer: '李明辉', suggest: '加速领用', level: 'amber' },
  { code: 'MAT-2024-1156', name: '高压螺栓M30', age: 168, amount: 48, quantity: 200, unit: '个', project: 'A-扩建', projectName: 'A-扩建', buyer: '张建国', suggest: '加速领用', level: 'amber' },
  { code: 'MAT-2024-1278', name: '电缆桥架', age: 155, amount: 42, quantity: 120, unit: '米', project: 'H-备品', projectName: 'H-备品', buyer: '周文博', suggest: '项目间调拨', level: 'amber' },
  { code: 'MAT-2025-0034', name: '防腐涂料', age: 142, amount: 38, quantity: 85, unit: '吨', project: 'F-安环', projectName: 'F-安环', buyer: '刘永刚', suggest: '加速领用', level: 'amber' },
  { code: 'MAT-2025-0123', name: '气动执行器', age: 128, amount: 35, quantity: 14, unit: '台', project: 'G-研发', projectName: 'G-研发', buyer: '杨海峰', suggest: '降级使用', level: 'amber' },
  { code: 'MAT-2025-0234', name: '配电柜配件', age: 115, amount: 32, quantity: 22, unit: '个', project: 'C-检修', projectName: 'C-检修', buyer: '王建华', suggest: '保留观察', level: 'amber' },
  { code: 'MAT-2025-0345', name: '焊接管件', age: 98, amount: 28, quantity: 55, unit: '个', project: 'I-基建', projectName: 'I-基建', buyer: '张建国', suggest: '加速领用', level: 'green' },
  { code: 'MAT-2025-0456', name: '液位计', age: 85, amount: 22, quantity: 9, unit: '台', project: 'E-运维', projectName: 'E-运维', buyer: '陈伟明', suggest: '保留观察', level: 'green' },
]

const SAMPLE_OVERSTOCK: OverstockItem[] = [
  { name: '高压开关柜配件', current: 480, safeMax: 200 },
  { name: '特种阀门DN200', current: 380, safeMax: 160 },
  { name: '防爆电缆', current: 350, safeMax: 180 },
  { name: '进口轴承', current: 220, safeMax: 120 },
  { name: '不锈钢管件', current: 200, safeMax: 100 },
  { name: 'PLC模块', current: 180, safeMax: 90 },
  { name: '仪表变送器', current: 165, safeMax: 85 },
  { name: '密封垫片', current: 140, safeMax: 70 },
  { name: '高压螺栓', current: 125, safeMax: 65 },
  { name: '电缆桥架', current: 110, safeMax: 60 },
]

const SAMPLE_CLEANUP: CleanupItem[] = [
  { project: 'A-扩建', total: 3200, cleaned: 1200, remain: 2000, rate: 38 },
  { project: 'B-技改', total: 2800, cleaned: 1800, remain: 1000, rate: 64 },
  { project: 'C-检修', total: 2100, cleaned: 600, remain: 1500, rate: 29 },
  { project: 'D-新建', total: 1500, cleaned: 1100, remain: 400, rate: 73 },
  { project: 'E-运维', total: 1200, cleaned: 800, remain: 400, rate: 67 },
  { project: 'F-安环', total: 950, cleaned: 850, remain: 100, rate: 89 },
  { project: 'G-研发', total: 780, cleaned: 200, remain: 580, rate: 26 },
  { project: 'H-备品', total: 650, cleaned: 350, remain: 300, rate: 54 },
  { project: 'I-基建', total: 520, cleaned: 450, remain: 70, rate: 87 },
  { project: 'J-IT', total: 380, cleaned: 350, remain: 30, rate: 92 },
]

const SAMPLE_SUGGEST: OptimizeSuggestItem[] = [
  { name: '阀门DN200', current: 380, dailyUse: 2.5, maxStock: 180 },
  { name: '电缆YJV', current: 350, dailyUse: 4.0, maxStock: 140 },
  { name: '轴承SKF', current: 220, dailyUse: 1.2, maxStock: 100 },
  { name: '管件Φ108', current: 200, dailyUse: 3.0, maxStock: 120 },
  { name: '变送器', current: 165, dailyUse: 1.5, maxStock: 80 },
  { name: '螺栓M30', current: 125, dailyUse: 2.0, maxStock: 70 },
  { name: '涂料', current: 85, dailyUse: 0.8, maxStock: 35 },
  { name: '执行器', current: 70, dailyUse: 0.6, maxStock: 30 },
]

// 处置建议 → 项目、采购人的启发式映射
const PROJECT_POOL = ['A-扩建', 'B-技改', 'C-检修', 'D-新建', 'E-运维', 'F-安环', 'G-研发', 'H-备品']
const BUYER_POOL = ['张建国', '李明辉', '王建华', '赵志强', '陈伟明', '刘永刚', '杨海峰', '周文博']

function hashToIndex(s: string, pool: string[]): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h) % pool.length
}

export const useTheme4Store = defineStore('theme4', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ═══ 图表数据 ═══
  const sluggishList = ref<SluggishItem[]>([])
  const overstockList = ref<OverstockItem[]>([])
  const cleanupList = ref<CleanupItem[]>([])
  const suggestList = ref<OptimizeSuggestItem[]>([])

  // ═══ 原始 API 返回值 ═══
  const topUnclaimedRaw = ref<TopUnclaimedItem[]>([])

  // ═══ KPI 卡片 ═══
  const kpiCards = computed<KpiCardData[]>(() => {
    const totalInventory = overstockList.value.reduce((s, i) => s + i.current, 0)
    const overStockCount = overstockList.value.filter(i => i.current / i.safeMax > 2).length
    const totalCleaned = cleanupList.value.reduce((s, i) => s + i.cleaned, 0)
    const avgCleanRate = cleanupList.value.length > 0
      ? cleanupList.value.reduce((s, i) => s + i.rate, 0) / cleanupList.value.length
      : 0

    return [
      {
        icon: '📋',
        label: '呆滞待处置项',
        value: sluggishList.value.length,
        unit: '项',
        change: `紧急 ${sluggishList.value.filter(i => i.level === 'red').length} 项`,
        changeType: 'down',
        color: '#10b981',
      },
      {
        icon: '📦',
        label: '呆滞库存总额',
        value: totalInventory || 2350,
        unit: '万元',
        change: `超量物料 ${overStockCount} 个`,
        changeType: 'down',
        color: '#f59e0b',
      },
      {
        icon: '⚠️',
        label: '超安全库存物料',
        value: overstockList.value.length,
        unit: '个',
        change: `超标>2.5x ${overstockList.value.filter(i => i.current / i.safeMax > 2.5).length} 个`,
        changeType: 'down',
        color: '#f43f5e',
      },
      {
        icon: '✅',
        label: '平均清理完成率',
        value: +avgCleanRate.toFixed(0),
        unit: '%',
        change: `已处置 ¥${totalCleaned} 万`,
        changeType: avgCleanRate >= 50 ? 'up' : 'down',
        color: '#3b82f6',
      },
    ]
  })

  // ═══ 将 API 数据转为 SluggishItem 格式 ═══
  function apiToSluggish(items: TopUnclaimedItem[]): SluggishItem[] {
    return items.map((item) => {
      const age = item.age_days
      const amount = +(item.inventory_amount / 10000).toFixed(0) || item.inventory_amount
      // 优先级 = 库龄 × 金额综合：紧急需同时满足高库龄+高金额
      let level: 'red' | 'amber' | 'green'
      if (age > 300 && amount >= 50) {
        level = 'red'
      } else if (age > 180 || amount >= 30) {
        level = 'amber'
      } else {
        level = 'green'
      }

      // 根据库龄和金额推荐处置建议
      let suggest: string
      if (age > 365) suggest = '报废处置'
      else if (age > 270) suggest = '折价转让'
      else if (age > 180) suggest = amount > 100 ? '项目间调拨' : '降级使用'
      else if (age > 90) suggest = amount > 60 ? '退回供应商' : '加速领用'
      else suggest = '保留观察'

      // 优先使用 API 返回的真实项目和采购人，无数据时降级到启发式映射
      const project = item.owner_project_code || ''
      const projectName = item.owner_project_name || ''
      const buyer = item.purchaser_name || ''

      return {
        code: item.material_code,
        name: item.material_name || item.material_code,
        age,
        amount,
        quantity: item.current_quantity || 0,
        unit: item.unit || '',
        project,
        projectName,
        buyer,
        suggest,
        level,
      }
    })
  }

  // ═══ 加载全部数据 ═══
  async function loadAllData() {
    loading.value = true
    error.value = null
    try {
      // 尝试从 API 获取 TOP 呆滞清单
      let topItems: TopUnclaimedItem[] = []
      let apiFailed = false
      try {
        topItems = await getTopUnclaimedAmount(15)
        topUnclaimedRaw.value = topItems
      } catch {
        apiFailed = true
      }

      // 呆滞清单：优先 API，降级用示例数据
      if (!apiFailed && topItems.length > 0) {
        sluggishList.value = apiToSluggish(topItems)
      } else {
        sluggishList.value = SAMPLE_SLUGGISH
      }

      // 优化建议：优先 API，降级用示例数据
      try {
        suggestList.value = await getOptimizeSuggest(8, 60)
      } catch {
        suggestList.value = SAMPLE_SUGGEST
      }

      // 超量备货 / 处置进度：使用示例数据
      overstockList.value = SAMPLE_OVERSTOCK
      cleanupList.value = SAMPLE_CLEANUP
    } catch (e: any) {
      console.error('主题四数据加载失败:', e)
      error.value = e?.message || '数据加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    kpiCards,
    sluggishList,
    overstockList,
    cleanupList,
    suggestList,
    loadAllData,
  }
})
