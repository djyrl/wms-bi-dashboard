<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getInventoryData } from '@/api/modules/inventory'
import type {
  UsageRatePoint, InOutPoint, WaterLevelItem, AnomalyDay,
  ProjectTreeNode, BuyerRankItem, CategoryBubbleItem, BatchDigestItem,
  AgePyramidItem, AgeTrendPoint, AgeGaugeItem,
  SluggishItem, OverstockItem, CleanupItem, OptimizeSuggestItem,
  KpiCardData,
} from '@/types/inventory'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import SectionHeader from '@/components/inventory/SectionHeader.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

// Theme 1
import UsageRateTrend from '@/components/inventory/claim/UsageRateTrend.vue'
import InboundOutboundCompare from '@/components/inventory/claim/InboundOutboundCompare.vue'
import WaterLevelChart from '@/components/inventory/claim/WaterLevelChart.vue'
import AnomalyCalendar from '@/components/inventory/claim/AnomalyCalendar.vue'

// Theme 2
import ProjectTreemap from '@/components/inventory/structure/ProjectTreemap.vue'
import BuyerRanking from '@/components/inventory/structure/BuyerRanking.vue'
import CategoryBubble from '@/components/inventory/structure/CategoryBubble.vue'
import BatchProgress from '@/components/inventory/structure/BatchProgress.vue'

// Theme 3
import AgePyramid from '@/components/inventory/time/AgePyramid.vue'
import AgeTrend from '@/components/inventory/time/AgeTrend.vue'
import SluggishHeatmap from '@/components/inventory/time/SluggishHeatmap.vue'
import AgeGauge from '@/components/inventory/time/AgeGauge.vue'

// Theme 4
import SluggishTable from '@/components/inventory/actions/SluggishTable.vue'
import OverstockChart from '@/components/inventory/actions/OverstockChart.vue'
import CleanupProgress from '@/components/inventory/actions/CleanupProgress.vue'
import OptimizeSuggest from '@/components/inventory/actions/OptimizeSuggest.vue'

const MONTHS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
const CATEGORIES = ['钢材', '电缆', '阀门', '泵类', '仪表', '管件', '紧固件', '密封件', '电器', '轴承']

const SAMPLE = {
  usageRate: [85, 83, 81, 80, 79, 77, 76, 74, 73, 72, 71, 72],
  usageTarget: [80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
  inAmount: [420, 380, 450, 520, 480, 510, 560, 490, 530, 550, 470, 500],
  outAmount: [380, 350, 390, 400, 370, 380, 390, 360, 370, 380, 340, 360],
  stockCurrent: [320, 280, 450, 180, 220, 350, 150, 200, 380, 120],
  stockSafeMax: [250, 200, 300, 150, 180, 250, 120, 160, 280, 100],
  stockSafeMin: [120, 100, 150, 80, 90, 120, 60, 80, 140, 50],
  projectTree: [
    { name: 'A-扩建', value: 3200, usageRate: 68 },
    { name: 'B-技改', value: 2800, usageRate: 75 },
    { name: 'C-检修', value: 2100, usageRate: 58 },
    { name: 'D-新建', value: 1500, usageRate: 82 },
    { name: 'E-运维', value: 1200, usageRate: 71 },
    { name: 'F-安环', value: 950, usageRate: 90 },
    { name: 'G-研发', value: 780, usageRate: 45 },
    { name: 'H-备品', value: 650, usageRate: 55 },
    { name: 'I-基建', value: 520, usageRate: 88 },
    { name: 'J-IT', value: 380, usageRate: 92 },
    { name: 'K-消防', value: 320, usageRate: 62 },
    { name: 'L-绿化', value: 180, usageRate: 95 },
  ] as ProjectTreeNode[],
  buyer: [
    { name: '张建国', value: 4500, usageRate: 65 },
    { name: '李明辉', value: 3800, usageRate: 72 },
    { name: '王建华', value: 2900, usageRate: 58 },
    { name: '赵志强', value: 2400, usageRate: 81 },
    { name: '陈伟明', value: 2100, usageRate: 69 },
    { name: '刘永刚', value: 1850, usageRate: 74 },
    { name: '杨海峰', value: 1200, usageRate: 53 },
    { name: '周文博', value: 950, usageRate: 88 },
  ] as BuyerRankItem[],
  categoryBubble: [
    { name: '钢材', inventory: 3200, usageRate: 68, skuCount: 320 },
    { name: '电缆', inventory: 2800, usageRate: 72, skuCount: 280 },
    { name: '阀门', inventory: 2100, usageRate: 55, skuCount: 210 },
    { name: '泵类', inventory: 1500, usageRate: 82, skuCount: 150 },
    { name: '仪表', inventory: 2400, usageRate: 60, skuCount: 240 },
    { name: '管件', inventory: 1800, usageRate: 75, skuCount: 180 },
    { name: '紧固件', inventory: 900, usageRate: 88, skuCount: 90 },
    { name: '密封件', inventory: 650, usageRate: 90, skuCount: 65 },
    { name: '电器', inventory: 2800, usageRate: 52, skuCount: 280 },
    { name: '轴承', inventory: 1200, usageRate: 78, skuCount: 120 },
  ] as CategoryBubbleItem[],
  batchLabels: ['入库月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月'],
  batch: [
    { name: '批次2401', color: '#3b82f6', data: [100, 82, 65, 48, 35, 22, 15] },
    { name: '批次2403', color: '#f59e0b', data: [100, 88, 78, 65, 55, 48, 40] },
    { name: '批次2405', color: '#f43f5e', data: [100, 92, 85, 80, 75, 72, 68] },
    { name: '批次2407', color: '#10b981', data: [100, 75, 55, 40, 30, 22, 18] },
  ] as BatchDigestItem[],
  ageLabels: ['0-30天', '30-60天', '60-90天', '90-180天', '180-365天', '>365天'],
  ageAmount: [2800, 3200, 1800, 1200, 650, 350],
  ageSku: [1200, 1800, 950, 620, 380, 210],
  avgAge: [35, 36, 38, 37, 40, 42, 43, 45, 47, 49, 50, 52],
  over90: [8, 9, 9, 10, 11, 12, 12, 13, 14, 15, 16, 17],
  heatmapBase: [
    [15, 12, 28, 8, 32, 18, 5, 3, 25, 10],
    [20, 18, 35, 12, 38, 22, 8, 5, 30, 14],
    [35, 28, 45, 22, 42, 32, 15, 12, 38, 20],
    [45, 38, 55, 32, 48, 42, 25, 20, 45, 28],
    [65, 55, 72, 48, 58, 55, 40, 32, 58, 42],
    [85, 78, 92, 68, 75, 72, 58, 48, 78, 62],
  ],
  heatmapAgeLabels: ['>365天', '180-365', '90-180', '60-90', '30-60', '0-30天'],
  ageGaugeProjects: ['A-扩建', 'B-技改', 'C-检修', 'D-新建', 'E-运维', 'F-安环', 'G-研发', 'H-备品'],
  ageGaugeAvgDays: [52, 45, 68, 32, 48, 28, 75, 55],
  over90Rate: [22, 18, 35, 8, 15, 5, 42, 28],
  sluggishItems: [
    { code: 'MAT-2023-0892', name: '高压开关柜配件', age: 385, amount: 186, project: 'C-检修', buyer: '王建华', suggest: '报废处置', level: 'red' as const },
    { code: 'MAT-2024-0156', name: '特种阀门DN200', age: 312, amount: 152, project: 'A-扩建', buyer: '张建国', suggest: '折价转让', level: 'red' as const },
    { code: 'MAT-2024-0234', name: '防爆电缆YJV22', age: 298, amount: 138, project: 'G-研发', buyer: '杨海峰', suggest: '项目间调拨', level: 'red' as const },
    { code: 'MAT-2024-0412', name: '进口轴承SKF', age: 265, amount: 95, project: 'B-技改', buyer: '李明辉', suggest: '降级使用', level: 'amber' as const },
    { code: 'MAT-2024-0567', name: '不锈钢管件Φ108', age: 242, amount: 88, project: 'C-检修', buyer: '王建华', suggest: '折价转让', level: 'amber' as const },
    { code: 'MAT-2024-0721', name: 'PLC控制模块', age: 228, amount: 76, project: 'D-新建', buyer: '赵志强', suggest: '退回供应商', level: 'amber' as const },
    { code: 'MAT-2024-0892', name: '仪表变送器', age: 205, amount: 65, project: 'E-运维', buyer: '陈伟明', suggest: '降级使用', level: 'amber' as const },
    { code: 'MAT-2024-1034', name: '密封垫片组件', age: 185, amount: 52, project: 'B-技改', buyer: '李明辉', suggest: '加速领用', level: 'amber' as const },
  ] as SluggishItem[],
  overstockItems: ['高压开关柜配件', '特种阀门DN200', '防爆电缆', '进口轴承', '不锈钢管件', 'PLC模块', '仪表变送器', '密封垫片', '高压螺栓', '电缆桥架'],
  overstockCurrent: [480, 380, 350, 220, 200, 180, 165, 140, 125, 110],
  overstockSafeMax: [200, 160, 180, 120, 100, 90, 85, 70, 65, 60],
  cleanupProjects: ['A-扩建', 'B-技改', 'C-检修', 'D-新建', 'E-运维', 'F-安环', 'G-研发', 'H-备品', 'I-基建', 'J-IT'],
  cleanupTotal: [3200, 2800, 2100, 1500, 1200, 950, 780, 650, 520, 380],
  cleanupCleaned: [1200, 1800, 600, 1100, 800, 850, 200, 350, 450, 350],
  suggestItems: ['阀门DN200', '电缆YJV', '轴承SKF', '管件Φ108', '变送器', '螺栓M30', '涂料', '执行器'],
  suggestCurrent: [380, 350, 220, 200, 165, 125, 85, 70],
  suggestDailyUse: [2.5, 4.0, 1.2, 3.0, 1.5, 2.0, 0.8, 0.6],
  suggestMaxStock: [180, 140, 100, 120, 80, 70, 35, 30],
}

const loading = ref(false)
const error = ref<string | null>(null)

const claimUsageRate = ref<UsageRatePoint[]>([])
const claimInOut = ref<InOutPoint[]>([])
const claimWaterLevel = ref<WaterLevelItem[]>([])
const claimAnomaly = ref<AnomalyDay[]>([])

const structureProjectTree = ref<ProjectTreeNode[]>([])
const structureBuyerRank = ref<BuyerRankItem[]>([])
const structureCategoryBubble = ref<CategoryBubbleItem[]>([])
const structureBatch = ref<BatchDigestItem[]>([])
const structureBatchLabels = ref<string[]>([])

const timePyramid = ref<AgePyramidItem[]>([])
const timeTrend = ref<AgeTrendPoint[]>([])
const timeHeatmapData = ref<number[][]>([])
const timeGauge = ref<AgeGaugeItem[]>([])

const topSluggish = ref<SluggishItem[]>([])
const topOverstock = ref<OverstockItem[]>([])
const topCleanup = ref<CleanupItem[]>([])
const topSuggest = ref<OptimizeSuggestItem[]>([])

const kpiCards = computed<KpiCardData[]>(() => [
  { icon: '📉', label: '当月物资领用率', value: 72.3, unit: '%', change: '↓ 4.2% vs 上月', changeType: 'down' as const, color: '#f43f5e' },
  { icon: '🔍', label: '库存来源项目数', value: 28, unit: '个', change: '↑ 3个 新增项目', changeType: 'down' as const, color: '#f59e0b' },
  { icon: '⏱', label: '全库平均库龄', value: 52, unit: '天', change: '↑ 17天 vs 年初', changeType: 'down' as const, color: '#8b5cf6' },
  { icon: '📋', label: '呆滞待处置项', value: 17, unit: '项', change: '↓ 5项 已处置', changeType: 'up' as const, color: '#10b981' },
])

function buildSampleData() {
  const { usageRate, usageTarget } = SAMPLE
  const n = usageRate.length
  const xs = usageRate.map((_, i) => i)
  const yMean = usageRate.reduce((a, b) => a + b, 0) / n
  const xMean = (n - 1) / 2
  const slope = xs.reduce((s, x, i) => s + (x - xMean) * (usageRate[i] - yMean), 0) /
    xs.reduce((s, x) => s + (x - xMean) * (x - xMean), 0)
  const intercept = yMean - slope * xMean
  const trendLine = usageRate.map((_, i) => +(slope * i + intercept).toFixed(1))

  claimUsageRate.value = MONTHS.map((m, i) => ({
    month: m, rate: usageRate[i], target: usageTarget[i], trend: trendLine[i],
  }))

  claimInOut.value = MONTHS.map((m, i) => ({
    month: m,
    inbound: SAMPLE.inAmount[i],
    outbound: SAMPLE.outAmount[i],
    net: SAMPLE.inAmount[i] - SAMPLE.outAmount[i],
  }))

  claimWaterLevel.value = CATEGORIES.map((c, i) => ({
    category: c,
    current: SAMPLE.stockCurrent[i],
    safeMax: SAMPLE.stockSafeMax[i],
    safeMin: SAMPLE.stockSafeMin[i],
  }))

  const anomalyDays: AnomalyDay[] = []
  const today = new Date()
  const anomalyLabels = ['正常', '入库异常', '领用异常', '双异常']
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const dateStr = `${d.getMonth() + 1}/${d.getDate()}`
    const r = Math.random()
    const v: 0 | 1 | 2 | 3 = r > 0.55 ? 1 : r > 0.35 ? 2 : r > 0.28 ? 3 : 0
    anomalyDays.push({ date: dateStr, type: v, label: anomalyLabels[v] })
  }
  claimAnomaly.value = anomalyDays

  structureProjectTree.value = SAMPLE.projectTree
  structureBuyerRank.value = SAMPLE.buyer
  structureCategoryBubble.value = SAMPLE.categoryBubble
  structureBatch.value = SAMPLE.batch
  structureBatchLabels.value = SAMPLE.batchLabels

  timePyramid.value = SAMPLE.ageLabels.map((range, i) => ({
    range, amount: SAMPLE.ageAmount[i], skuCount: SAMPLE.ageSku[i],
  }))

  const ageVals = SAMPLE.avgAge
  const ax = ageVals.map((_, i) => i)
  const ayMean = ageVals.reduce((a, b) => a + b, 0) / ageVals.length
  const axMean = (ageVals.length - 1) / 2
  const aSlope = ax.reduce((s, x, i) => s + (x - axMean) * (ageVals[i] - ayMean), 0) /
    ax.reduce((s, x) => s + (x - axMean) * (x - axMean), 0)
  const aIntercept = ayMean - aSlope * axMean
  const aTrend = ageVals.map((_, i) => +(aSlope * i + aIntercept).toFixed(1))

  timeTrend.value = MONTHS.map((m, i) => ({
    month: m, avgAge: ageVals[i], trend: aTrend[i], over90Rate: SAMPLE.over90[i],
  }))

  timeHeatmapData.value = SAMPLE.heatmapBase

  timeGauge.value = SAMPLE.ageGaugeProjects.map((p, i) => ({
    project: p, avgAgeDays: SAMPLE.ageGaugeAvgDays[i], over90Rate: SAMPLE.over90Rate[i],
  }))

  topSluggish.value = SAMPLE.sluggishItems

  topOverstock.value = SAMPLE.overstockItems.map((name, i) => ({
    name,
    current: SAMPLE.overstockCurrent[i],
    safeMax: SAMPLE.overstockSafeMax[i],
  }))

  topCleanup.value = SAMPLE.cleanupProjects.map((p, i) => {
    const total = SAMPLE.cleanupTotal[i]
    const cleaned = SAMPLE.cleanupCleaned[i]
    return { project: p, total, cleaned, remain: total - cleaned, rate: +(cleaned / total * 100).toFixed(0) }
  })

  topSuggest.value = SAMPLE.suggestItems.map((name, i) => ({
    name,
    current: SAMPLE.suggestCurrent[i],
    dailyUse: SAMPLE.suggestDailyUse[i],
    maxStock: SAMPLE.suggestMaxStock[i],
  }))
}

async function loadAllData() {
  loading.value = true
  error.value = null
  try {
    const remote = await getInventoryData()
    if (remote) {
      buildSampleData()
    } else {
      buildSampleData()
    }
  } catch {
    buildSampleData()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载库存分析数据..." class="inventory-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══════════ 主题一：领用指标 ═══════════ -->
      <SectionHeader :num="1" title="领用指标 · 识别库存形成情况" desc="总体控制，发现库存异常增长信号" color="#f43f5e" />

      <div class="chart-grid">
        <ChartCard title="📉 物资领用率月度趋势">
          <template #actions>
            <span class="card-subtitle">领用金额 / (期初库存 + 本期入库) × 100%</span>
          </template>
          <UsageRateTrend :data="claimUsageRate" :months="MONTHS" />
        </ChartCard>
        <ChartCard title="📦 入库金额 vs 领用金额 对比">
          <template #actions>
            <span class="card-subtitle">当月入库多、领用少 → 库存净增</span>
          </template>
          <InboundOutboundCompare :data="claimInOut" :months="MONTHS" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="📊 在库水位变化 · 安全库存偏离度">
          <WaterLevelChart :data="claimWaterLevel" />
        </ChartCard>
        <ChartCard title="⚠️ 库存异常变动预警日历">
          <template #actions>
            <span class="card-subtitle">单日入库/领用偏离均值2σ的事件</span>
          </template>
          <AnomalyCalendar :data="claimAnomaly" />
        </ChartCard>
      </div>

      <!-- ═══════════ 主题二：结构指标 ═══════════ -->
      <SectionHeader :num="2" title="结构指标 · 定位库存来源" desc="按项目/采购人/类别逐层下钻，找到库存形成的关键来源" color="#f59e0b" />

      <div class="chart-grid">
        <ChartCard title="🌳 按项目维度 · 库存金额分布">
          <template #actions>
            <span class="card-subtitle">矩形面积 = 库存金额，点击可下钻</span>
          </template>
          <ProjectTreemap :data="structureProjectTree" />
        </ChartCard>
        <ChartCard title="👤 按采购负责人 · 库存贡献排行">
          <template #actions>
            <span class="card-subtitle">定位高库存的责任主体</span>
          </template>
          <BuyerRanking :data="structureBuyerRank" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="🏷 按物料类别 · 库存金额与领用率">
          <template #actions>
            <span class="card-subtitle">气泡大小=库存金额，颜色=领用率</span>
          </template>
          <CategoryBubble :data="structureCategoryBubble" />
        </ChartCard>
        <ChartCard title="📦 按入库批次 · 库存消化进度">
          <template #actions>
            <span class="card-subtitle">批次入库后逐月剩余库存占比</span>
          </template>
          <BatchProgress :data="structureBatch" :labels="structureBatchLabels" />
        </ChartCard>
      </div>

      <!-- ═══════════ 主题三：时间指标 ═══════════ -->
      <SectionHeader :num="3" title="时间指标 · 识别滞留库存" desc="库龄结构变化，精准定位长期未动物料" color="#8b5cf6" />

      <div class="chart-grid">
        <ChartCard title="⏳ 库存库龄分布 · 金字塔">
          <template #actions>
            <span class="card-subtitle">横向对比库龄段金额与SKU数</span>
          </template>
          <AgePyramid :data="timePyramid" />
        </ChartCard>
        <ChartCard title="📈 平均库龄月度趋势">
          <template #actions>
            <span class="card-subtitle">整体库龄健康度变化方向</span>
          </template>
          <AgeTrend :data="timeTrend" :months="MONTHS" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="🔥 滞留库存热力图 · 物料类别 × 库龄段">
          <template #actions>
            <span class="card-subtitle">颜色越深=库存金额越高，聚焦右下角(超长库龄)</span>
          </template>
          <SluggishHeatmap :data="timeHeatmapData" :categories="CATEGORIES" :age-labels="SAMPLE.heatmapAgeLabels" />
        </ChartCard>
        <ChartCard title="🚨 库龄预警仪表 · 各项目超标情况">
          <template #actions>
            <span class="card-subtitle">超过90天库龄的库存占比</span>
          </template>
          <AgeGauge :data="timeGauge" />
        </ChartCard>
      </div>

      <!-- ═══════════ 主题四：TOP指标 · 问题清单 ═══════════ -->
      <SectionHeader :num="4" title="TOP指标 · 问题清单 & 行动计划" desc="按优先级排序，每一项都有明确的处置建议" color="#10b981" />

      <div class="chart-grid">
        <ChartCard title="📋 TOP9 呆滞物料 · 处置优先级清单">
          <template #actions>
            <span class="card-subtitle">按「金额×库龄」综合评分排序</span>
          </template>
          <SluggishTable :data="topSluggish" />
        </ChartCard>
        <ChartCard title="📊 TOP10 超量备货物料">
          <template #actions>
            <span class="card-subtitle">当前库存 / 安全库存上限</span>
          </template>
          <OverstockChart :data="topOverstock" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="✅ 处置计划执行进度">
          <template #actions>
            <span class="card-subtitle">各项目呆滞物资清理完成率</span>
          </template>
          <CleanupProgress :data="topCleanup" />
        </ChartCard>
        <ChartCard title="💡 智能备货优化建议">
          <template #actions>
            <span class="card-subtitle">基于日均消耗量推荐安全库存调整</span>
          </template>
          <OptimizeSuggest :data="topSuggest" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.inventory-dashboard {
  padding: 0 0 24px;
}

/* ── CSS Grid 布局（与参考 HTML 一致）── */
.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 4px;

  /* 所有卡片自动等高，图表完美对齐 */
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
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
