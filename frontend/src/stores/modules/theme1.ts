import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getClaimWeekly,
  getStructureByCategory,
  getAnomalyDaily,
  getWmsSummary,
  getWmsClaim,
} from '@/api/modules/theme1'
import type {
  ClaimWeeklyRes,
  CategoryRes,
  AnomalyDailyRes,
  WmsSummary,
  WmsClaim,
} from '@/api/modules/theme1'
import type {
  UsageRatePoint,
  InOutPoint,
  WaterLevelItem,
  AnomalyDay,
  KpiCardData,
} from '@/types/inventory'

export const useTheme1Store = defineStore('theme1', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ═══ 图表数据 ═══
  const claimUsageRate = ref<UsageRatePoint[]>([])
  const claimInOut = ref<InOutPoint[]>([])
  const claimWaterLevel = ref<WaterLevelItem[]>([])
  const claimAnomaly = ref<AnomalyDay[]>([])

  // ═══ 原始 API 返回值（供页面 Header 展示） ═══
  const summary = ref<WmsSummary | null>(null)
  const claim = ref<WmsClaim | null>(null)

  const weeks = ref<string[]>([])

  // ---- KPI 卡片 ----
  const kpiCards = computed<KpiCardData[]>(() => {
    const s = summary.value
    const c = claim.value
    return [
      {
        icon: '📉',
        label: '采购领用率（金额）',
        value: c?.claim_rate_amount ?? 0,
        unit: '%',
        change: `未领用 ${c?.unclaimed_amount_ratio ?? 0}%`,
        changeType: (c?.claim_rate_amount ?? 0) >= 70 ? 'up' : 'down',
        color: '#f43f5e',
      },
      {
        icon: '📦',
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
        icon: '📋',
        label: '当前库存总额',
        value: s?.total_inventory_amount ?? 0,
        unit: '万元',
        change: `已领用 ${c?.total_claimed_amount ?? 0} 万元`,
        changeType: 'up',
        color: '#10b981',
      },
    ]
  })

  // ---- 线性回归趋势线 ----
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

  // ---- 加载所有数据 ----
  async function loadAllData() {
    loading.value = true
    error.value = null
    try {
      const [weeklyRes, categoryRes, anomalyRes, summaryRes, claimRes] =
        await Promise.all([
          getClaimWeekly(),
          getStructureByCategory(),
          getAnomalyDaily(30),
          getWmsSummary(),
          getWmsClaim(),
        ])

      summary.value = summaryRes
      claim.value = claimRes

      // -- 1. 领用率趋势（按周） --
      const rawWeekly = weeklyRes as ClaimWeeklyRes
      weeks.value = rawWeekly.weeks || []
      const rates = rawWeekly.data.map((d) => d.claim_rate)
      const trends = calcTrend(rates)
      claimUsageRate.value = rawWeekly.data.map((d, i) => ({
        month: d.week,
        rate: d.claim_rate,
        target: 20,
        trend: trends[i],
      }))

      // -- 2. 入库 vs 领用对比（按周） --
      claimInOut.value = rawWeekly.data.map((d) => ({
        month: d.week,
        inbound: d.inbound_amount,
        outbound: d.claimed_amount,
        net: d.net_amount,
      }))

      // -- 3. 在库水位 --
      const rawCat = categoryRes as CategoryRes
      claimWaterLevel.value = rawCat.data.map((d) => ({
        materialCode: d.material_code,
        category: d.category,
        current: d.current,
        safeMax: d.safe_max,
        safeMin: d.safe_min,
      }))

      // -- 4. 异常预警日历 --
      const rawAnom = anomalyRes as AnomalyDailyRes
      claimAnomaly.value = rawAnom.data.map((d) => ({
        date: d.date,
        type: d.type,
        label: d.label,
      }))
    } catch (e: any) {
      error.value = e?.message || '数据加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    weeks,
    kpiCards,
    claimUsageRate,
    claimInOut,
    claimWaterLevel,
    claimAnomaly,
    loadAllData,
  }
})
