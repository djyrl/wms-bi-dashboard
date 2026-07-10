import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getTimeIndicators,
  getAgeLayers,
  getByProject,
  getAgeMonthly,
  getAgeHeatmap,
} from '@/api/modules/theme3'
import type {
  TimeIndicatorsRes,
  AgeLayerItem,
  WmsProjectIndicator,
  AgeMonthlyRes,
  AgeHeatmapRes,
} from '@/api/modules/theme3'
import type {
  AgePyramidItem,
  AgeTrendPoint,
  AgeGaugeItem,
  KpiCardData,
} from '@/types/inventory'

export const useTheme3Store = defineStore('theme3', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ═══ 图表数据 ═══
  const agePyramid = ref<AgePyramidItem[]>([])
  const ageTrend = ref<AgeTrendPoint[]>([])
  const sluggishHeatmap = ref<number[][]>([])
  const heatmapCategories = ref<string[]>([])
  const heatmapAgeLabels = ref<string[]>([])
  const ageGauge = ref<AgeGaugeItem[]>([])

  // ═══ 原始 API 返回值 ═══
  const timeIndicators = ref<TimeIndicatorsRes | null>(null)
  const ageLayers = ref<AgeLayerItem[]>([])
  const projectIndicators = ref<WmsProjectIndicator[]>([])
  const ageMonthlyData = ref<AgeMonthlyRes | null>(null)

  const months = ref<string[]>([])

  // ═══ KPI 卡片 ═══
  const kpiCards = computed<KpiCardData[]>(() => {
    const t = timeIndicators.value
    const projs = projectIndicators.value
    return [
      {
        icon: '⏱',
        label: '加权平均库龄',
        value: t?.avg_age_weighted_days ?? 52,
        unit: '天',
        change: t ? `${t.avg_age_weighted_days > 45 ? '⚠️ 偏高' : '✅ 正常'}` : '--',
        changeType: (t?.avg_age_weighted_days ?? 52) <= 45 ? 'up' : 'down',
        color: '#8b5cf6',
      },
      {
        icon: '📦',
        label: '库存总额',
        value: t ? +(t.age_structure.reduce((s, i) => s + i.amount, 0) / 10000).toFixed(2) : 0,
        unit: '万元',
        change: t ? `${t.age_structure.length} 个库龄段` : '--',
        changeType: 'up',
        color: '#3b82f6',
      },
      {
        icon: '⚠️',
        label: '长库龄占比(≥1年)',
        value: t ? +(t.aged_ratio_1y * 100).toFixed(1) : 17,
        unit: '%',
        change: t ? `金额 ¥${t.aged_amount_1y.toFixed(0)} 万` : '--',
        changeType: (t?.aged_ratio_1y ?? 0) <= 0.15 ? 'up' : 'down',
        color: '#f43f5e',
      },
      {
        icon: '🏗',
        label: '覆盖项目',
        value: projs.length || 8,
        unit: '个',
        change: projs.length > 0 ? `≥90天滞留 ${ageGauge.value.filter(g => g.over90Rate > 15).length} 个` : '--',
        changeType: 'up',
        color: '#10b981',
      },
    ]
  })

  // ═══ 线性回归趋势线（与 theme1 一致） ═══
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

  // ═══ 将 API 数据转为图表格式 ═══
  function buildChartData(
    t: TimeIndicatorsRes,
    projs: WmsProjectIndicator[],
    ageMonthly: AgeMonthlyRes | null,
    heatmap: AgeHeatmapRes | null,
  ) {
    // -- 1. 库龄金字塔（优先用 API 的 age_structure） --
    if (t.age_structure && t.age_structure.length > 0) {
      agePyramid.value = t.age_structure.map(item => ({
        range: item.range,
        amount: item.amount,
        skuCount: item.count,
      }))
    }

    // -- 2. 平均库龄月度趋势（从后台取真实数据 + 线性回归趋势线） --
    if (ageMonthly && ageMonthly.data.length > 0) {
      months.value = ageMonthly.months
      const avgAges = ageMonthly.data.map(d => d.avg_age)
      const trendVals = calcTrend(avgAges)
      ageTrend.value = ageMonthly.data.map((d, i) => ({
        month: d.month,
        avgAge: d.avg_age,
        trend: trendVals[i],
        over90Rate: d.over90_rate,
      }))
    }

    // -- 3. 滞留热力图（从后台取按物料类别 × 库龄段聚合的真实数据） --
    if (heatmap && heatmap.data.length > 0) {
      sluggishHeatmap.value = heatmap.data
      heatmapCategories.value = heatmap.categories
      heatmapAgeLabels.value = heatmap.age_labels
    }

    // -- 4. 库龄预警仪表（用 by-project 返回的真实 avg_age_days + over90_ratio） --
    if (projs.length > 0) {
      ageGauge.value = projs
        .map(p => ({
          project: p.project_code,
          avgAgeDays: p.avg_age_days,
          over90Rate: p.over90_ratio,
        }))
        .sort((a, b) => b.avgAgeDays - a.avgAgeDays)
        .slice(0, 8)
    }
  }

  // ═══ 加载全部数据 ═══
  async function loadAllData() {
    loading.value = true
    error.value = null
    try {
      const [t, layers, projs, ageMonthly, heatmap] = await Promise.all([
        getTimeIndicators(),
        getAgeLayers({ min_amount: 0, min_age: 0 }),
        getByProject(),
        getAgeMonthly(),
        getAgeHeatmap(),
      ])

      timeIndicators.value = t
      ageLayers.value = layers
      projectIndicators.value = projs
      ageMonthlyData.value = ageMonthly

      buildChartData(t, projs, ageMonthly, heatmap)
    } catch (e: any) {
      console.error('主题三数据加载失败:', e)
      error.value = e?.message || '数据加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    months,
    kpiCards,
    agePyramid,
    ageTrend,
    sluggishHeatmap,
    heatmapCategories,
    heatmapAgeLabels,
    ageGauge,
    timeIndicators,
    loadAllData,
  }
})
