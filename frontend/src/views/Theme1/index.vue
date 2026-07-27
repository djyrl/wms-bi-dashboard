<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getClaimDaily,
  getClaimWeekly,
  getClaimMonthly,
  getClaimYearly,
  getStructureByCategory,
  getAnomalyDaily,
  getWmsSummary,
  getWmsClaim,
} from '@/api/modules/theme1'
import type { WmsSummary, WmsClaimSplit } from '@/api/modules/theme1'
import type { UsageRatePoint, InOutPoint, WaterLevelItem, AnomalyDay, KpiCardData } from '@/types/inventory'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import UsageRateTrend from '@/components/inventory/claim/UsageRateTrend.vue'
import InboundOutboundCompare from '@/components/inventory/claim/InboundOutboundCompare.vue'
import WaterLevelChart from '@/components/inventory/claim/WaterLevelChart.vue'
import AnomalyCalendar from '@/components/inventory/claim/AnomalyCalendar.vue'

type TimeGranularity = 'day' | 'week' | 'month' | 'year'

const GRANULARITY_LABELS: Record<TimeGranularity, string> = {
  day: '日',
  week: '周',
  month: '月',
  year: '年',
}

const loading = ref(false)
const error = ref<string | null>(null)

const timeGranularity = ref<TimeGranularity>('week')
const timeLabels = ref<string[]>([])

const summary = ref<WmsSummary | null>(null)
const claim = ref<WmsClaimSplit | null>(null)

const claimUsageRate = ref<UsageRatePoint[]>([])
const claimInOut = ref<InOutPoint[]>([])
const claimWaterLevel = ref<WaterLevelItem[]>([])
const claimAnomaly = ref<AnomalyDay[]>([])

const granularityLabel = computed(() => GRANULARITY_LABELS[timeGranularity.value])
const chartTitle = computed(() => {
  const label = granularityLabel.value
  return {
    rate: `物资领用率趋势（按${label}）`,
    inOut: `入库金额 vs 领用金额 对比（按${label}）`,
  }
})

const kpiCards = computed<KpiCardData[]>(() => {
  const s = summary.value
  const c = claim.value?.all
  return [
    {
      icon: '\u{1F4C9}',
      label: '采购领用率（金额）',
      value: c?.claim_rate_amount ?? 0,
      unit: '%',
      change: `未领用 ${c?.unclaimed_amount_ratio ?? 0}%`,
      changeType: (c?.claim_rate_amount ?? 0) >= 70 ? 'up' : 'down',
      color: '#f43f5e',
    },
    {
      icon: '\u{1F4E6}',
      label: '入库总额',
      value: s?.total_inbound_amount ?? 0,
      unit: '万元',
      change: `${s?.total_records ?? 0} 条记录`,
      changeType: 'up',
      color: '#f59e0b',
    },
    {
      icon: '⏱',
      label: '加权平均库龄',
      value: s?.avg_age_weighted_days ?? 0,
      unit: '天',
      change: `长库龄(≥1年)占比 ${((s?.aged_ratio_1y ?? 0) * 100).toFixed(1)}%`,
      changeType: (s?.avg_age_weighted_days ?? 0) <= 90 ? 'up' : 'down',
      color: '#8b5cf6',
    },
    {
      icon: '\u{1F4CB}',
      label: '当前库存总额',
      value: s?.total_inventory_amount ?? 0,
      unit: '万元',
      change: `已领用 ${c?.total_claimed_amount ?? 0} 万元`,
      changeType: 'up',
      color: '#10b981',
    },
  ]
})

function calcTrend(values: number[]): number[] {
  const n = values.length
  if (n < 2) return values.map(() => values[0] ?? 0)
  const xs = values.map((_, i) => i)
  const yMean = values.reduce((a, b) => a + b, 0) / n
  const xMean = (n - 1) / 2
  const slope =
    xs.reduce((s, x, i) => s + (x - xMean) * (values[i] - yMean), 0) /
    xs.reduce((s, x) => s + (x - xMean) * (x - xMean), 0)
  const intercept = yMean - slope * xMean
  return values.map((_, i) => +(slope * i + intercept).toFixed(1))
}

function setGranularity(g: TimeGranularity) {
  timeGranularity.value = g
  loadAllData()
}

async function loadAllData() {
  loading.value = true
  error.value = null
  const errs: string[] = []
  const g = timeGranularity.value

  try { summary.value = await getWmsSummary() } catch (e: any) { errs.push('总览: ' + (e?.message || '失败')) }
  try { claim.value = await getWmsClaim() } catch (e: any) { errs.push('领用指标: ' + (e?.message || '失败')) }

  try {
    if (g === 'day') {
      const raw = await getClaimDaily()
      timeLabels.value = raw.days || []
      const rates = raw.data.map((d) => d.claim_rate)
      const trends = calcTrend(rates)
      claimUsageRate.value = raw.data.map((d, i) => ({ month: d.day, rate: d.claim_rate, target: 20, trend: trends[i] }))
      claimInOut.value = raw.data.map((d) => ({ month: d.day, inbound: d.inbound_amount, outbound: d.claimed_amount, net: d.net_amount }))
    } else if (g === 'week') {
      const raw = await getClaimWeekly()
      timeLabels.value = raw.weeks || []
      const rates = raw.data.map((d) => d.claim_rate)
      const trends = calcTrend(rates)
      claimUsageRate.value = raw.data.map((d, i) => ({ month: d.week, rate: d.claim_rate, target: 20, trend: trends[i] }))
      claimInOut.value = raw.data.map((d) => ({ month: d.week, inbound: d.inbound_amount, outbound: d.claimed_amount, net: d.net_amount }))
    } else if (g === 'month') {
      const raw = await getClaimMonthly()
      timeLabels.value = raw.months || []
      const rates = raw.data.map((d) => d.claim_rate)
      const trends = calcTrend(rates)
      claimUsageRate.value = raw.data.map((d, i) => ({ month: d.month, rate: d.claim_rate, target: 20, trend: trends[i] }))
      claimInOut.value = raw.data.map((d) => ({ month: d.month, inbound: d.inbound_amount, outbound: d.claimed_amount, net: d.net_amount }))
    } else {
      const raw = await getClaimYearly()
      timeLabels.value = raw.years || []
      const rates = raw.data.map((d) => d.claim_rate)
      const trends = calcTrend(rates)
      claimUsageRate.value = raw.data.map((d, i) => ({ month: d.year, rate: d.claim_rate, target: 20, trend: trends[i] }))
      claimInOut.value = raw.data.map((d) => ({ month: d.year, inbound: d.inbound_amount, outbound: d.claimed_amount, net: d.net_amount }))
    }
  } catch (e: any) { errs.push('领用率趋势: ' + (e?.message || '失败')) }

  try {
    const rawCat = await getStructureByCategory()
    claimWaterLevel.value = rawCat.data.map((d) => ({
      materialCode: d.material_code,
      category: d.category,
      current: d.current,
      safeMax: d.safe_max,
      safeMin: d.safe_min,
    }))
  } catch (e: any) { errs.push('在库水位: ' + (e?.message || '失败')) }

  try {
    let days = 30
    if (g === 'week') days = 180
    else if (g === 'month') days = 365
    else if (g === 'year') days = 365 * 2
    const rawAnom = await getAnomalyDaily(days)
    claimAnomaly.value = rawAnom.data.map((d) => ({
      date: d.date,
      type: d.type,
      label: d.label,
    }))
  } catch (e: any) { errs.push('异常预警: ' + (e?.message || '失败')) }

  if (errs.length > 0) error.value = errs.join('；')
  loading.value = false
}

const granularityOptions: { label: string; value: TimeGranularity }[] = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' },
]

function handleGranularityChange(value: string | number | boolean | undefined) {
  setGranularity(value as TimeGranularity)
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载领用分析数据..." class="theme1-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <div class="chart-grid">
        <ChartCard :title="'📉 ' + chartTitle.rate">
          <template #actions>
            <span class="card-subtitle">领用金额 / 本期入库 × 100%</span>
          </template>
          <UsageRateTrend :data="claimUsageRate" :months="timeLabels" />
        </ChartCard>
        <ChartCard :title="'📦 ' + chartTitle.inOut">
          <template #actions>
            <span class="card-subtitle">入库多、领用少 → 库存净增</span>
          </template>
          <InboundOutboundCompare :data="claimInOut" :months="timeLabels" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="📊 在库物资 · 安全库存偏离度">
          <WaterLevelChart :data="claimWaterLevel" />
        </ChartCard>
        <ChartCard title="⚠️ 库存异常变动预警日历">
          <template #actions>
            <span class="card-subtitle">领用金额异常波动检测（新项目 / 环比 / 同比）</span>
          </template>
          <AnomalyCalendar :data="claimAnomaly" />
        </ChartCard>
      </div>

      <!-- ═══ 时间粒度切换 ═══ -->
      <div class="granularity-bar">
        <span class="granularity-label">时间粒度：</span>
        <el-radio-group
          :model-value="timeGranularity"
          size="small"
          @change="handleGranularityChange"
        >
          <el-radio-button
            v-for="opt in granularityOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme1-dashboard {
  padding: 0 0 24px;
}

.granularity-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;

  .granularity-label {
    font-size: 14px;
    color: #64748b;
  }
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
