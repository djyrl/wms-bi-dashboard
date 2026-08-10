<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
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
import { getWmsSummary } from '@/api/modules/theme1'
import type { AgePyramidItem, AgeTrendPoint, AgeGaugeItem, KpiCardData } from '@/types/inventory'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import AgePyramid from '@/components/inventory/time/AgePyramid.vue'
import AgeTrend from '@/components/inventory/time/AgeTrend.vue'
import SluggishHeatmap from '@/components/inventory/time/SluggishHeatmap.vue'
import AgeGauge from '@/components/inventory/time/AgeGauge.vue'

const loading = ref(false)
const error = ref<string | null>(null)

const agePyramid = ref<AgePyramidItem[]>([])
const ageTrend = ref<AgeTrendPoint[]>([])
const sluggishHeatmap = ref<number[][]>([])
const heatmapCategories = ref<string[]>([])
const heatmapAgeLabels = ref<string[]>([])
const ageGauge = ref<AgeGaugeItem[]>([])

const timeIndicators = ref<TimeIndicatorsRes | null>(null)
const wmsSummary = ref<any>(null)
const ageLayers = ref<AgeLayerItem[]>([])
const projectIndicators = ref<WmsProjectIndicator[]>([])
const ageMonthlyData = ref<AgeMonthlyRes | null>(null)

const months = ref<string[]>([])

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
      value: wmsSummary.value?.total_inventory_amount ?? 0,
      unit: '万元',
      change: wmsSummary.value ? `${wmsSummary.value.total_records} 个批次` : '--',
      changeType: 'up',
      color: '#3b82f6',
    },
    {
      icon: '⚠️',
      label: '长库龄占比(≥1年)',
      value: t ? +(t.aged_ratio_1y * 100).toFixed(1) : 17,
      unit: '%',
      change: t ? `金额 ¥${(t.aged_amount_1y / 10000).toFixed(0)} 万` : '--',
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

function buildChartData(
  t: TimeIndicatorsRes,
  projs: WmsProjectIndicator[],
  ageMonthly: AgeMonthlyRes | null,
  heatmap: AgeHeatmapRes | null,
) {
  if (t.age_structure && t.age_structure.length > 0) {
    agePyramid.value = t.age_structure.map(item => ({
      range: item.range,
      amount: +(item.amount / 10000).toFixed(2),
      skuCount: item.count,
    }))
  }

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

  if (heatmap && heatmap.data.length > 0) {
    sluggishHeatmap.value = heatmap.data
    heatmapCategories.value = heatmap.categories
    heatmapAgeLabels.value = heatmap.age_labels
  }

  if (projs.length > 0) {
    ageGauge.value = projs
      .filter(p => p.project_name !== '非项目物资')
      .map(p => ({
        project: p.project_code,
        projectName: (p.project_name && p.project_name !== p.project_code) ? p.project_name : p.project_code,
        avgAgeDays: p.avg_age_days,
        over90Rate: p.over90_ratio,
      }))
      .sort((a, b) => b.avgAgeDays - a.avgAgeDays)
      .slice(0, 8)
  }
}

async function loadAllData() {
  loading.value = true
  error.value = null

  const errs: string[] = []
  let t: TimeIndicatorsRes | null = null
  let projs: WmsProjectIndicator[] = []
  let ageMonthly: AgeMonthlyRes | null = null
  let heatmap: AgeHeatmapRes | null = null

  try { wmsSummary.value = await getWmsSummary() } catch (e: any) { errs.push('WMS总览: ' + (e?.message || '失败')) }
  try { t = await getTimeIndicators() } catch (e: any) { errs.push('时间指标: ' + (e?.message || '失败')) }
  try { ageLayers.value = await getAgeLayers({ min_amount: 0, min_age: 0 }) } catch (e: any) { errs.push('库龄分层: ' + (e?.message || '失败')) }
  try { projs = await getByProject() } catch (e: any) { errs.push('项目分析: ' + (e?.message || '失败')) }
  try { const r = await getAgeMonthly(); ageMonthlyData.value = r; ageMonthly = r } catch (e: any) { errs.push('库龄趋势: ' + (e?.message || '失败')) }
  try { heatmap = await getAgeHeatmap() } catch (e: any) { errs.push('热力图: ' + (e?.message || '失败')) }

  if (t) {
    timeIndicators.value = t
    projectIndicators.value = projs
    buildChartData(t, projs, ageMonthly, heatmap)
  }

  if (errs.length > 0) {
    error.value = errs.join('；')
  }
  loading.value = false
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载库龄分析数据..." class="theme3-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══ 第一行：库龄金字塔 + 平均库龄趋势 ═══ -->
      <div class="chart-grid">
        <ChartCard title="⏳ 库存库龄分布 · 金字塔">
          <template #actions>
            <span class="card-subtitle">横向对比库龄段金额与SKU数</span>
          </template>
          <AgePyramid :data="agePyramid" />
        </ChartCard>
        <ChartCard title="📈 平均库龄月度趋势">
          <template #actions>
            <span class="card-subtitle">整体库龄健康度变化方向</span>
          </template>
          <AgeTrend :data="ageTrend" :months="months" />
        </ChartCard>
      </div>

      <!-- ═══ 第二行：滞留热力图 + 库龄预警 ═══ -->
      <div class="chart-grid">
        <ChartCard title="🔥 滞留库存热力图 · 物料类别 × 库龄段">
          <template #actions>
            <span class="card-subtitle">聚焦右下角（超长库龄）</span>
          </template>
          <SluggishHeatmap
            :data="sluggishHeatmap"
            :categories="heatmapCategories"
            :ageLabels="heatmapAgeLabels"
          />
        </ChartCard>
        <ChartCard title="🚨 库龄预警 · 各项目超标情况">
          <template #actions>
            <span class="card-subtitle">超过90天库龄的库存占比</span>
          </template>
          <AgeGauge :data="ageGauge" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme3-dashboard {
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
