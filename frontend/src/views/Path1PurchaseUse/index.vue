<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  getClaimDaily,
  getClaimWeekly,
  getClaimMonthly,
  getClaimYearly,
  getStructureByCategory,
  getAnomalyDaily,
  getWmsSummary,
  getWmsClaim,
  getErpClaim,
} from '@/api/modules/theme1'
import type {
  WmsSummary,
  WmsClaimSplit,
  ErpClaimSplit,
} from '@/api/modules/theme1'
import type { UsageRatePoint, InOutPoint, WaterLevelItem, AnomalyDay, KpiCardData } from '@/types/inventory'
import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'
import UsageRateTrend from '@/components/inventory/claim/UsageRateTrend.vue'
import InboundOutboundCompare from '@/components/inventory/claim/InboundOutboundCompare.vue'
import WaterLevelChart from '@/components/inventory/claim/WaterLevelChart.vue'
import AnomalyCalendar from '@/components/inventory/claim/AnomalyCalendar.vue'

type TimeGranularity = 'day' | 'week' | 'month' | 'year'
const GRANULARITY_LABELS: Record<TimeGranularity, string> = { day: '日', week: '周', month: '月', year: '年' }

const router = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)
const timeGranularity = ref<TimeGranularity>('week')
const timeLabels = ref<string[]>([])
const summary = ref<WmsSummary | null>(null)
const claim = ref<WmsClaimSplit | null>(null)
const erpClaim = ref<ErpClaimSplit | null>(null)
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
  const ec = erpClaim.value?.year
  return [
    { icon: '\u{1F4C9}', label: '采购领用率（金额）', value: ec?.claim_rate_amount ?? 0, unit: '%', change: `未领用 ${ec?.unclaimed_amount_ratio ?? 0}%`, changeType: (ec?.claim_rate_amount ?? 0) >= 70 ? 'up' : 'down', color: '#f43f5e' },
    { icon: '\u{1F4E6}', label: '入库总额', value: ec?.total_inbound_amount ?? 0, unit: '万元', change: `出库 ${ec?.total_outbound_amount?.toFixed(0) ?? 0} 万元`, changeType: 'up', color: '#f59e0b' },
    { icon: '⏱', label: '加权平均库龄', value: s?.avg_age_weighted_days ?? 0, unit: '天', change: `长库龄(≥1年)占比 ${((s?.aged_ratio_1y ?? 0) * 100).toFixed(1)}%`, changeType: (s?.avg_age_weighted_days ?? 0) <= 90 ? 'up' : 'down', color: '#8b5cf6' },
    { icon: '\u{1F4CB}', label: '当前库存总额', value: s?.total_inventory_amount ?? 0, unit: '万元', change: `库存记录 ${s?.total_records ?? 0} 条`, changeType: 'up', color: '#10b981' },
  ]
})

function calcTrend(values: number[]): number[] {
  const n = values.length
  if (n < 2) return values.map(() => values[0] ?? 0)
  const xs = values.map((_, i) => i)
  const yMean = values.reduce((a, b) => a + b, 0) / n
  const xMean = (n - 1) / 2
  const slope = xs.reduce((s, x, i) => s + (x - xMean) * (values[i] - yMean), 0) /
    xs.reduce((s, x) => s + (x - xMean) * (x - xMean), 0)
  const intercept = yMean - slope * xMean
  return values.map((_, i) => +(slope * i + intercept).toFixed(1))
}

const opts = [{ label: '日', value: 'day' as const }, { label: '周', value: 'week' as const }, { label: '月', value: 'month' as const }, { label: '年', value: 'year' as const }]

async function loadAllData() {
  loading.value = true
  error.value = null
  const errs: string[] = []
  const g = timeGranularity.value
  try { summary.value = await getWmsSummary() } catch (e: any) { errs.push('总览: ' + (e?.message || '失败')) }
  try { claim.value = await getWmsClaim() } catch (e: any) { errs.push('领用指标: ' + (e?.message || '失败')) }
  try { erpClaim.value = await getErpClaim() } catch (e: any) { errs.push('ERP领用率: ' + (e?.message || '失败')) }
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
    claimWaterLevel.value = rawCat.data.filter(d => d.material_code !== '-').map((d) => ({ materialCode: d.material_code, category: d.category, current: d.current, safeMax: d.safe_max, safeMin: d.safe_min }))
  } catch (e: any) { errs.push('在库水位: ' + (e?.message || '失败')) }
  try {
    let days = 30
    if (g === 'week') days = 180
    else if (g === 'month') days = 365
    else if (g === 'year') days = 365 * 2
    const rawAnom = await getAnomalyDaily(days)
    claimAnomaly.value = rawAnom.data.map((d) => ({ date: d.date, inbound_amount: d.inbound_amount, claimed_amount: d.claimed_amount, type: d.type, label: d.label, huanbi: d.huanbi }))
  } catch (e: any) { errs.push('异常预警: ' + (e?.message || '失败')) }
  if (errs.length > 0) error.value = errs.join('；')
  loading.value = false
}

function setGranularity(v: TimeGranularity) {
  timeGranularity.value = v
  loadAllData()
}

onMounted(() => loadAllData())
</script>

<template>
  <div v-loading="loading" class="page">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />
    <template v-if="!error">
      <el-button circle class="back-float" @click="router.push('/')" title="返回上级页面">←</el-button>
      <!-- <h2>📥📤📦 采消存分析 · 买了多少 → 用了多少 → 剩多少</h2> -->
      <KpiCards :cards="kpiCards" />
      <div class="grid">
        <ChartCard :title="'📉 ' + chartTitle.rate"><template #actions><span class="sub">领用金额 / 入库金额 × 100%</span></template><UsageRateTrend :data="claimUsageRate" :months="timeLabels" :granularity="granularityLabel" /></ChartCard>
        <ChartCard :title="'📦 ' + chartTitle.inOut"><template #actions><span class="sub">入库 vs 领用，净增 = 入库 - 领用</span></template><InboundOutboundCompare :data="claimInOut" :months="timeLabels" :granularity="granularityLabel" /></ChartCard>
      </div>
      <div class="grid">
        <ChartCard title="📊 安全库存偏离"><WaterLevelChart :data="claimWaterLevel" /></ChartCard>
        <ChartCard title="⚠️ 异常变动预警（近12周）">
          <template #actions>
            <span class="sub">规则：① 近30天新建项目 ② 周领用环比波动 &gt; ±30%</span>
          </template>
          <AnomalyCalendar :data="claimAnomaly" />
        </ChartCard>
      </div>
      <div class="bar">
        <el-radio-group :model-value="timeGranularity" size="small" @change="(v: string | number | boolean | undefined) => setGranularity(v as TimeGranularity)">
          <el-radio-button v-for="o in opts" :key="o.value" :value="o.value">{{ o.label }}</el-radio-button>
        </el-radio-group>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0 0 24px; }
h2 { font-size: 20px; margin-bottom: 16px; }
.back-float { position: fixed; top: 12px; left: 12px; z-index: 200; width: 26px; height: 26px; min-width: 26px; padding: 0; border: 1px solid #e2e8f0; background: rgba(255,255,255,0.88); backdrop-filter: blur(6px); box-shadow: 0 1px 4px rgba(0,0,0,0.06); font-size: 13px; color: #94a3b8; }
.back-float:hover { color: #3b82f6; border-color: #3b82f6; background: #fff; }
.bar { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; font-size: 14px; color: #64748b; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 4px; }
.sub { font-size: 10px; color: #94a3b8; }
@media (max-width: 1024px) { .grid { grid-template-columns: 1fr; } }
</style>
