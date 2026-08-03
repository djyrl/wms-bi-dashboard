<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  getTimeIndicators,
  getAgeLayers,
  getByProject,
  getAgeMonthly,
  getAgeHeatmap,
} from '@/api/modules/theme3'
import { getErpAge } from '@/api/modules/theme1'
import type {
  TimeIndicatorsRes,
  WmsProjectIndicator,
  AgeMonthlyRes,
  AgeHeatmapRes,
} from '@/api/modules/theme3'
import type { AgePyramidItem, AgeTrendPoint, AgeGaugeItem, KpiCardData } from '@/types/inventory'
import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'
import AgePyramid from '@/components/inventory/time/AgePyramid.vue'
import AgeTrend from '@/components/inventory/time/AgeTrend.vue'
import SluggishHeatmap from '@/components/inventory/time/SluggishHeatmap.vue'
import AgeGauge from '@/components/inventory/time/AgeGauge.vue'

const router = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)

const agePyramid = ref<AgePyramidItem[]>([])
const ageTrend = ref<AgeTrendPoint[]>([])
const sluggishHeatmap = ref<number[][]>([])
const heatmapCategories = ref<string[]>([])
const heatmapAgeLabels = ref<string[]>([])
const ageGauge = ref<AgeGaugeItem[]>([])

const timeIndicators = ref<TimeIndicatorsRes | null>(null)
const erpAge = ref<any>(null)
const projectIndicators = ref<WmsProjectIndicator[]>([])
const ageMonthlyData = ref<AgeMonthlyRes | null>(null)

const kpiCards = computed<KpiCardData[]>(() => {
  const t = timeIndicators.value
  const ea = erpAge.value
  const projs = projectIndicators.value
  return [
    { icon: '⏱', label: '加权平均库龄', value: ea?.avg_age_weighted_days ?? t?.avg_age_weighted_days ?? 52, unit: '天', change: (ea?.avg_age_weighted_days ?? t?.avg_age_weighted_days ?? 52) > 45 ? '⚠️ 偏高' : '✅ 正常', changeType: (ea?.avg_age_weighted_days ?? t?.avg_age_weighted_days ?? 52) <= 45 ? 'up' : 'down', color: '#8b5cf6' },
    { icon: '📦', label: '库存总额 (ERP)', value: ea?.total_inventory_amt ?? 0, unit: '万元', change: ea ? `${ea.total_batches} 个批次` : '--', changeType: 'up', color: '#3b82f6' },
    { icon: '⚠️', label: '长库龄占比(≥1年)', value: ea?.aged_ratio_1y ?? +(t?.aged_ratio_1y * 100).toFixed(1) ?? 17, unit: '%', change: ea ? `金额 ¥${ea.aged_amount_1y} 万` : '--', changeType: (ea?.aged_ratio_1y ?? 17) <= 15 ? 'up' : 'down', color: '#f43f5e' },
    { icon: '🏗', label: '覆盖项目', value: projs.length || 8, unit: '个', change: projs.length > 0 ? `≥90天滞留 ${ageGauge.value.filter(g => g.over90Rate > 15).length} 个` : '--', changeType: 'up', color: '#10b981' },
  ]
})

function calcTrend(values: number[]): number[] {
  const n = values.length
  if (n < 2) return values.map(() => values[0] ?? 0)
  const xs = values.map((_, i) => i)
  const yMean = values.reduce((a, b) => a + b, 0) / n
  const xMean = (n - 1) / 2
  const slope = xs.reduce((s, x, i) => s + (x - xMean) * (values[i] - yMean), 0) / xs.reduce((s, x) => s + (x - xMean) * (x - xMean), 0)
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
    agePyramid.value = t.age_structure
      .filter(item => item.range !== '≥5年')
      .map(item => ({ range: item.range, amount: +(item.amount / 10000).toFixed(2), skuCount: item.count }))
  }
  if (ageMonthly && ageMonthly.data.length > 0) {
    const avgAges = ageMonthly.data.map(d => d.avg_age)
    const trendVals = calcTrend(avgAges)
    ageTrend.value = ageMonthly.data.map((d, i) => ({ month: d.month, avgAge: d.avg_age, trend: trendVals[i], over90Rate: d.over90_rate }))
  }
  if (heatmap && heatmap.data.length > 0) {
    sluggishHeatmap.value = heatmap.data
    heatmapCategories.value = heatmap.categories
    heatmapAgeLabels.value = heatmap.age_labels
  }
  if (projs.length > 0) {
    ageGauge.value = projs
      .filter(p => p.project_name && p.project_name !== '非项目物资')
      .map(p => ({ project: p.project_code, projectName: p.project_name, avgAgeDays: p.avg_age_days, over90Rate: p.over90_ratio, unclaimedAmount: p.unclaimed_amount }))
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
  try { t = await getTimeIndicators() } catch (e: any) { errs.push('时间指标: ' + (e?.message || '失败')) }
  try { erpAge.value = await getErpAge() } catch (e: any) { errs.push('ERP库龄: ' + (e?.message || '失败')) }
  try { await getAgeLayers({ min_amount: 0, min_age: 0 }) } catch (e: any) { errs.push('库龄分层: ' + (e?.message || '失败')) }
  try { projs = await getByProject() } catch (e: any) { errs.push('项目分析: ' + (e?.message || '失败')) }
  try { const r = await getAgeMonthly(); ageMonthlyData.value = r; ageMonthly = r } catch (e: any) { errs.push('库龄趋势: ' + (e?.message || '失败')) }
  try { heatmap = await getAgeHeatmap() } catch (e: any) { errs.push('热力图: ' + (e?.message || '失败')) }
  if (t) {
    timeIndicators.value = t
    projectIndicators.value = projs
    buildChartData(t, projs, ageMonthly, heatmap)
  }
  if (errs.length > 0) error.value = errs.join('；')
  loading.value = false
}

onMounted(() => loadAllData())
</script>

<template>
  <div v-loading="loading" class="page">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />
    <template v-if="!error">
      <el-button circle class="back-float" @click="router.push('/')" title="返回上级页面">←</el-button>
      <!-- <h2>⏱⚠️🧹 库龄清理 · 放了多久 → 哪些要清理</h2> -->
      <KpiCards :cards="kpiCards" />
      <div class="grid">
        <ChartCard title="📊 加权平均库龄月度趋势">
          <template #actions><span class="sub">红线=趋势，柱=≥90天占比</span></template>
          <AgeTrend :data="ageTrend" :months="ageTrend.map(d => d.month)" />
        </ChartCard>
        <ChartCard title="🔻 库龄分布">
          <template #actions><span class="sub">各库龄段库存金额分布</span></template>
          <AgePyramid :data="agePyramid" />
        </ChartCard>
      </div>
      <div class="grid">
        <ChartCard title="🔥 物料类别 × 库龄段 热力图">
          <template #actions><span class="sub">颜色越深金额越大</span></template>
          <SluggishHeatmap :data="sluggishHeatmap" :categories="heatmapCategories" :ageLabels="heatmapAgeLabels" />
        </ChartCard>
        <ChartCard title="⚠️ 库龄预警仪表"><template #actions>
          <span class="sub">TOP 8 项目库龄排名</span></template>
          <AgeGauge :data="ageGauge" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0 0 24px; }
h2 { font-size: 20px; margin-bottom: 16px; }
.back-float { position: fixed; top: 12px; left: 12px; z-index: 200; width: 26px; height: 26px; min-width: 26px; padding: 0; border: 1px solid #e2e8f0; background: rgba(255,255,255,0.88); backdrop-filter: blur(6px); box-shadow: 0 1px 4px rgba(0,0,0,0.06); font-size: 13px; color: #94a3b8; }
.back-float:hover { color: #3b82f6; border-color: #3b82f6; background: #fff; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 4px; }
.sub { font-size: 10px; color: #94a3b8; }
@media (max-width: 1024px) { .grid { grid-template-columns: 1fr; } }
</style>
