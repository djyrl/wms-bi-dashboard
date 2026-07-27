<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getTopUnclaimedAmount, getOptimizeSuggest } from '@/api/modules/theme4'
import type { TopUnclaimedItem } from '@/api/modules/theme4'
import type { SluggishItem, OverstockItem, CleanupItem, OptimizeSuggestItem, KpiCardData } from '@/types/inventory'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import SluggishTable from '@/components/inventory/actions/SluggishTable.vue'
import OptimizeSuggest from '@/components/inventory/actions/OptimizeSuggest.vue'

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

const loading = ref(false)
const error = ref<string | null>(null)

const sluggishList = ref<SluggishItem[]>([])
const overstockList = ref<OverstockItem[]>([])
const cleanupList = ref<CleanupItem[]>([])
const suggestList = ref<OptimizeSuggestItem[]>([])
const topUnclaimedRaw = ref<TopUnclaimedItem[]>([])

const kpiCards = computed<KpiCardData[]>(() => {
  const totalInventory = overstockList.value.reduce((s, i) => s + i.current, 0)
  const overStockCount = overstockList.value.filter(i => i.current / i.safeMax > 2).length
  const totalCleaned = cleanupList.value.reduce((s, i) => s + i.cleaned, 0)
  const avgCleanRate = cleanupList.value.length > 0
    ? cleanupList.value.reduce((s, i) => s + i.rate, 0) / cleanupList.value.length
    : 0

  return [
    {
      icon: '📋', label: '优化建议项', value: sluggishList.value.length, unit: '项',
      change: `紧急 ${sluggishList.value.filter(i => i.level === 'red').length} 项`, changeType: 'down', color: '#10b981',
    },
    {
      icon: '📦', label: '呆滞库存总额', value: totalInventory || 2350, unit: '万元',
      change: `超量物料 ${overStockCount} 个`, changeType: 'down', color: '#f59e0b',
    },
    {
      icon: '⚠️', label: '超安全库存物料', value: overstockList.value.length, unit: '个',
      change: `超标>2.5x ${overstockList.value.filter(i => i.current / i.safeMax > 2.5).length} 个`, changeType: 'down', color: '#f43f5e',
    },
    {
      icon: '✅', label: '平均清理完成率', value: +avgCleanRate.toFixed(0), unit: '%',
      change: `已处置 ¥${totalCleaned} 万`, changeType: avgCleanRate >= 50 ? 'up' : 'down', color: '#3b82f6',
    },
  ]
})

function apiToSluggish(items: TopUnclaimedItem[]): SluggishItem[] {
  return items.map((item) => {
    const age = item.age_days
    const amount = +(item.inventory_amount / 10000).toFixed(0) || item.inventory_amount
    let level: 'red' | 'amber' | 'green'
    if (age > 300 && amount >= 50) level = 'red'
    else if (age > 180 || amount >= 30) level = 'amber'
    else level = 'green'

    let suggest: string
    if (age > 365) suggest = '报废处置'
    else if (age > 270) suggest = '折价转让'
    else if (age > 180) suggest = amount > 100 ? '项目间调拨' : '降级使用'
    else if (age > 90) suggest = amount > 60 ? '退回供应商' : '加速领用'
    else suggest = '保留观察'

    return {
      code: item.material_code,
      name: item.material_name || item.material_code,
      age,
      amount,
      quantity: item.current_quantity || 0,
      unit: item.unit || '',
      project: item.owner_project_code || '',
      projectName: item.owner_project_name || '',
      buyer: item.purchaser_name || '',
      suggest,
      level,
    }
  })
}

async function loadAllData() {
  loading.value = true
  error.value = null
  try {
    let topItems: TopUnclaimedItem[] = []
    let apiFailed = false
    try {
      topItems = await getTopUnclaimedAmount(15)
      topUnclaimedRaw.value = topItems
    } catch {
      apiFailed = true
    }

    if (!apiFailed && topItems.length > 0) {
      sluggishList.value = apiToSluggish(topItems)
    } else {
      sluggishList.value = SAMPLE_SLUGGISH
    }

    try {
      suggestList.value = await getOptimizeSuggest(8, 60)
    } catch {
      suggestList.value = SAMPLE_SUGGEST
    }

    overstockList.value = SAMPLE_OVERSTOCK
    cleanupList.value = SAMPLE_CLEANUP
  } catch (e: any) {
    console.error('主题四数据加载失败:', e)
    error.value = e?.message || '数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载行动计划数据..." class="theme4-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══ 4.1 TOP15 呆滞物料清单（全宽表格） ═══ -->
      <ChartCard title="📋 TOP15 呆滞物料 · 处置优先级清单">
        <template #actions>
          <span class="card-subtitle">按「金额×库龄」综合评分排序</span>
        </template>
        <SluggishTable :data="sluggishList" />
      </ChartCard>

      <!-- ═══ 4.2 超量备货 + 4.3 处置进度 ═══ -->
      <!-- <div class="chart-grid">
        <ChartCard title="📊 TOP10 超量备货物料">
          <template #actions>
            <span class="card-subtitle">当前库存 / 安全库存上限</span>
          </template>
          <OverstockChart :data="overstockList" />
        </ChartCard>
        <ChartCard title="✅ 处置计划执行进度">
          <template #actions>
            <span class="card-subtitle">各项目呆滞物资清理完成率</span>
          </template>
          <CleanupProgress :data="cleanupList" />
        </ChartCard>
      </div> -->

      <!-- ═══ 4.4 智能备货优化建议 ═══ -->
      <!-- <div class="chart-grid"> -->
        <ChartCard title="💡 智能备货优化建议">
          <template #actions>
            <span class="card-subtitle">基于日均消耗量推荐安全库存调整</span>
          </template>
          <OptimizeSuggest :data="suggestList" />
        </ChartCard>
      <!-- </div> -->
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme4-dashboard {
  padding: 0 0 24px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 4px;

  > .el-card {
    display: flex;
    flex-direction: column;

    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  }
}

.card-subtitle {
  font-size: 10px;
  color: #94a3b8;
}

@media (max-width: 1024px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
