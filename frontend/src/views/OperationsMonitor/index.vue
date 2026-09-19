<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch, nextTick } from 'vue'
import { useECharts } from '@/composables/useECharts'
import { getWmsSummary, getAnomalyDaily, getErpClaim, getStructureByCategory } from '@/api/modules/theme1'
import type { ErpClaimSplit } from '@/api/modules/theme1'
import { getStructure } from '@/api/modules/theme2'
import type { WmsStructure } from '@/api/modules/theme2'
import { getTopUnclaimedAmount } from '@/api/modules/theme4'
import type { AnomalyDay, WaterLevelItem } from '@/types/inventory'
import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import AnomalyCalendar from '@/components/inventory/claim/AnomalyCalendar.vue'
import WaterLevelChart from '@/components/inventory/claim/WaterLevelChart.vue'
import { formatDays } from '@/utils/format'
import { filterExcluded } from '@/utils/excludeMaterials'

const loading = ref(false)
const error = ref<string | null>(null)
const summary = ref<any>(null)
const erpClaim = ref<ErpClaimSplit | null>(null)
const anomalyDays = ref<AnomalyDay[]>([])
const structure = ref<WmsStructure | null>(null)
const topUnclaimed = ref<any[]>([])
const waterLevelData = ref<WaterLevelItem[]>([])
const sluggishRows = ref<any[]>([])
const projectBarRef = ref<HTMLDivElement>()
const projectBar = useECharts()

// ═══ 数据加载 ═══
async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [s, ec, ad, st, ta, sc] = await Promise.all([
      getWmsSummary(),
      getErpClaim(),
      getAnomalyDaily(30),
      getStructure(),
      getTopUnclaimedAmount(15),
      getStructureByCategory(),
    ])
    summary.value = s
    erpClaim.value = ec
    structure.value = st

    // 安全库存偏离度
    const scData = (sc as any)?.data || sc || []
    const scArr = Array.isArray(scData) ? scData : []
    waterLevelData.value = scArr.slice(0, 10).map((item: any) => ({
      materialCode: item.material_code || item.materialCode,
      category: item.category || item.material_code || '',
      current: item.current,
      safeMax: item.safe_max ?? item.safeMax,
      safeMin: item.safe_min ?? item.safeMin,
    }))

    // 异常检测
    const rawAd: any = ad?.data || ad || []
    anomalyDays.value = rawAd as AnomalyDay[]

    // 呆滞物料 TOP10
    const taFiltered = filterExcluded(ta || [])
    topUnclaimed.value = taFiltered
    sluggishRows.value = taFiltered.slice(0, 10).map((item: any, i: number) => ({
      rank: i + 1,
      code: item.material_code,
      name: item.material_name,
      amount: +(item.inventory_amount / 10000).toFixed(2),
      quantity: item.current_quantity,
      unit: item.unit || '',
      age: item.age_days,
      project: item.owner_project_name || item.owner_project_code || '-',
      buyer: item.purchaser_name || '-',
      level: item.age_days > 365 ? 'red' : item.age_days > 180 ? 'amber' : 'green',
    }))

  } catch (e: any) {
    error.value = e.message || '加载失败'
  }
  loading.value = false
}

// ═══ 计算属性 ═══
// KPI 状态判定
const kpiStatus = (val: number, target: number, inverse = false) => {
  const ratio = val / target
  if (inverse) return ratio <= 1 ? 'ok' : ratio <= 1.3 ? 'warning' : 'alert'
  return ratio >= 1 ? 'ok' : ratio >= 0.7 ? 'warning' : 'alert'
}
const statusConfig: Record<string, { color: string; label: string; icon: string }> = {
  ok: { color: '#10b981', label: '达标', icon: '✅' },
  warning: { color: '#f59e0b', label: '关注', icon: '⚠️' },
  alert: { color: '#f43f5e', label: '预警', icon: '🔴' },
}

const monitorKpis = computed(() => {
  const ec = erpClaim.value
  const s = summary.value
  return [
    {
      key: 'M1', name: '未领用金额（当年）',
      value: ec?.year?.unclaimed_amount ?? 0,
      unit: '万元', target: '越低越好',
      status: kpiStatus(20, ec?.year?.unclaimed_amount_ratio ?? 0, true),
      detail: `净入库 ${ec?.year?.net_inbound_amount?.toFixed(0) ?? '--'} 万  |  出库 ${ec?.year?.total_outbound_amount?.toFixed(0) ?? '--'} 万`,
    },
    {
      key: 'M2', name: '未领用金额占比',
      value: ec?.year?.unclaimed_amount_ratio ?? 0,
      unit: '%', target: '≤20%',
      status: kpiStatus(20, ec?.year?.unclaimed_amount_ratio ?? 0, true),
      detail: `= ${ec?.year?.unclaimed_amount?.toFixed(0) ?? '--'} 万 / ${ec?.year?.net_inbound_amount?.toFixed(0) ?? '--'} 万`,
    },
    {
      key: 'M3', name: '库龄 ≥ 1 年库存金额',
      value: s?.aged_amount_1y ?? 0,
      unit: '万元', target: '越低越好',
      status: kpiStatus(15, s?.aged_ratio_1y ?? 0, true),
      detail: `占总库存 ${s?.aged_ratio_1y?.toFixed(1) ?? '--'}%  |  总库存 ${s?.total_inventory_amount?.toFixed(0) ?? '--'} 万`,
    },
    {
      key: 'M4', name: '长库龄金额占比',
      value: s?.aged_ratio_1y ?? 0,
      unit: '%', target: '≤15%',
      status: kpiStatus(15, s?.aged_ratio_1y ?? 0, true),
      detail: `金额：${(s?.aged_amount_1y ?? 0).toFixed(2)} 万元`,
    },
  ]
})

// 固定调色板：活泼多彩系
const BAR_COLORS = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']

function renderProjectBar() {
  const projs = (structure.value?.project_ratios || [])
    .filter((p: any) => p.project_name && p.project_name !== '非项目物资')
    .slice(0, 8)
  if (!projectBarRef.value || !projs.length) return
  if (!projectBar.instance) projectBar.init(projectBarRef.value)
  projectBar.setOption({
    tooltip: { trigger: 'axis', formatter: (params: any) => `${projs[params[0].dataIndex]?.project_name || params[0].name}<br/>库存: ${params[0].value} 万` },
    grid: { left: 10, right: 10, top: 10, bottom: 50 },
    xAxis: { type: 'category', data: projs.map((p: any) => (p.project_name || '').length > 6 ? (p.project_name || '').slice(0, 6) + '…' : p.project_name), axisLabel: { rotate: 30, fontSize: 10, color: '#8a9aa9' }, axisLine: { lineStyle: { color: 'rgb(255 255 255 / 15%)' } } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}万', color: '#8a9aa9' }, splitLine: { lineStyle: { color: 'rgb(255 255 255 / 8%)' } } },
    series: [{
      type: 'bar',
      data: projs.map((p: any, i: number) => ({ value: +((p.inventory_amount || 0) / 10000).toFixed(0), itemStyle: { color: BAR_COLORS[i], borderRadius: [4, 4, 0, 0] } })),
    }],
  })
}

watch(() => structure.value?.project_ratios, () => nextTick(renderProjectBar))

// ═══ 全屏 ═══
const isFullscreen = ref(false)
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}
function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
  ;[300, 600, 1000].forEach(d => {
    setTimeout(() => {
      projectBar.resize()
      window.dispatchEvent(new Event('resize'))
    }, d)
  })
}

// 实时时钟
const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | null = null
function formatTime(d: Date) {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
function formatNum(v: number | null | undefined) {
  if (v == null) return '--'
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtWan(v: number) { return v ? (v / 10000).toFixed(2) : '0.00' }
function fmtAge(days: number | undefined | null): string {
  if (days == null) return '-'
  return formatDays(days)
}
function truncateText(text: string, maxLen = 20): string {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '…' : text
}

onMounted(() => {
  loadAll()
  setTimeout(renderProjectBar, 500)
  timer = setInterval(() => { now.value = new Date() }, 1000)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})
</script>

<template>
  <div v-loading="loading" class="ops-page">
    <ErrorResult v-if="error" :message="error" @retry="loadAll" />

    <template v-if="!error && summary">
      <!-- ═══ 顶部标题栏 ═══ -->
      <div class="page-header">
        <div class="page-header__left">
          <h2 class="page-title">📡 运营监控</h2>
          <span class="page-subtitle">{{ formatTime(now) }}</span>
        </div>
        <div class="status-summary">
          <span class="status-chip ok"><span class="chip-dot"></span>达标 {{ monitorKpis.filter(k => k.status === 'ok').length }}</span>
          <span class="status-chip warning"><span class="chip-dot"></span>关注 {{ monitorKpis.filter(k => k.status === 'warning').length }}</span>
          <span class="status-chip alert"><span class="chip-dot"></span>预警 {{ monitorKpis.filter(k => k.status === 'alert').length }}</span>
        </div>
        <span class="header-fs-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏展示'">⛶</span>
      </div>

      <!-- ═══ 核心监控指标 M1-M4 ═══ -->
      <div class="section section--kpi">
        <div class="kpi-grid kpi-grid--4col">
          <div v-for="kpi in monitorKpis" :key="kpi.key"
            class="kpi-card"
            :class="`kpi-card--${kpi.status}`"
          >
            <div class="kpi-card__header">
              <span class="kpi-card__name">{{ kpi.name }}</span>
              <span class="kpi-card__status" :style="{ color: statusConfig[kpi.status].color }">
                {{ statusConfig[kpi.status].icon }} {{ statusConfig[kpi.status].label }}
              </span>
            </div>
            <div class="kpi-card__body">
              <div class="kpi-card__value-row">
                <span class="kpi-card__value" :style="{ color: statusConfig[kpi.status].color }">
                  {{ typeof kpi.value === 'number' ? formatNum(kpi.value) : kpi.value }}
                </span>
                <span class="kpi-card__unit">{{ kpi.unit }}</span>
              </div>
              <div class="kpi-card__target">
                <span class="label">目标：</span>{{ kpi.target }}
              </div>
              <div class="kpi-card__detail">{{ kpi.detail }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 趋势与异常 ═══ -->
      <div class="section section--grow">
        <div class="chart-grid chart-grid--2col">
          <ChartCard title="🔥 库存异常变动预警日历（近30天）">
            <AnomalyCalendar :data="anomalyDays" :hideDetail="true" />
          </ChartCard>
          <ChartCard title="🌳 项目库存金额分布">
            <div ref="projectBarRef" class="chart"></div>
          </ChartCard>
        </div>
      </div>

      <!-- ═══ 库存结构分析 ═══ -->
      <div class="section section--grow">
        <div class="chart-grid chart-grid--2col">
          <!-- 未领用库存 -->
          <ChartCard :title="'📦 未领用库存'">
            <table class="mini-table" v-if="topUnclaimed?.length">
              <tr v-for="item in topUnclaimed" :key="item.id">
                <td>
                  <el-tooltip :content="item.material_name" placement="top" :disabled="(item.material_name || '').length <= 20">
                    <span>{{ truncateText(item.material_name) }}</span>
                  </el-tooltip>
                </td>
                <td class="num" style="color:#f87171">{{ fmtWan(item.inventory_amount) }} 万</td>
                <td class="num" style="font-size:11px;color:#8a9aa9">{{ fmtAge(item.age_days) }}</td>
              </tr>
            </table>
          </ChartCard>

          <!-- 安全库存偏离度 -->
          <ChartCard title="安全库存偏离度">
            <WaterLevelChart :data="waterLevelData" :hideDetail="true" />
          </ChartCard>
        </div>
      </div>

      <!-- ═══ 呆滞处置清单 ═══ -->
      <!-- <div class="section">
        <ChartCard title="TOP10 呆滞物料 · 处置优先级">
          <table class="data-table" v-if="sluggishRows.length">
            <thead>
              <tr>
                <th style="text-align:center">#</th>
                <th>物料编码</th>
                <th>物料名称</th>
                <th style="text-align:right">金额(万元)</th>
                <th style="text-align:right">数量</th>
                <th style="text-align:right">库龄(天)</th>
                <th>归属项目</th>
                <th>采购人</th>
                <th>处置建议</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sluggishRows" :key="item.code" :class="{ 'row-alert': item.level === 'red' }">
                <td style="text-align:center">
                  <span class="rank-badge" :class="item.rank <= 3 ? `rank-${item.rank}` : ''">{{ item.rank }}</span>
                </td>
                <td><code>{{ item.code }}</code></td>
                <td><span class="ellipsis-text">{{ item.name }}</span></td>
                <td class="num">{{ item.amount.toLocaleString() }}</td>
                <td class="num">{{ item.quantity }} {{ item.unit }}</td>
                <td class="num">
                  <span :style="{ color: item.age > 365 ? '#f43f5e' : item.age > 180 ? '#f59e0b' : '#10b981' }">{{ formatDays(item.age) }}</span>
                </td>
                <td>{{ item.project }}</td>
                <td>{{ item.buyer }}</td>
                <td>
                  <span class="action-tag" :class="`action-tag--${item.level}`">
                    {{ item.age > 365 ? '报废处置' : item.age > 180 ? '折价转让' : item.age > 90 ? '加速领用' : '保留观察' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </ChartCard>
      </div> -->
    </template>
  </div>
</template>

<style lang="scss" scoped>
// ═══ 页面整体 ═══
.ops-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 0 16px 16px;
  background: rgb(2, 4, 8);
  color: #e2e8f0;
}

// ═══ 页面头部 ═══
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 16px 20px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgb(30 41 59 / 80%) 0%, rgb(15 23 42 / 90%) 100%);
  border: 1px solid rgb(255 255 255 / 8%);
  flex-wrap: wrap;
  gap: 12px;
  flex-shrink: 0;
}
.page-header__left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #a855f7);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}
.page-subtitle {
  color: #00d4ff;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}
.header-fs-btn {
  cursor: pointer;
  font-size: 18px;
  color: #8a9aa9;
  transition: color 0.2s;
  &:hover { color: #00d4ff; }
}

// ═══ 状态摘要 ═══
.status-summary {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.status-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  background: rgb(255 255 255 / 5%);
  &.ok { color: #10b981; .chip-dot { background: #10b981; } }
  &.warning { color: #f59e0b; .chip-dot { background: #f59e0b; } }
  &.alert { color: #f43f5e; .chip-dot { background: #f43f5e; } }
}
.chip-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

// ═══ Section ═══
.section {
  margin-bottom: 16px;
  &--kpi { flex-shrink: 0; }
  &--grow {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
}
.section-desc {
  font-size: 12px;
  color: #8a9aa9;
}

// ═══ KPI 卡片网格 ═══
.kpi-grid {
  display: grid;
  gap: 12px;
  &--4col { grid-template-columns: repeat(4, 1fr); }
  &--2col { grid-template-columns: repeat(2, 1fr); }
}
.kpi-card {
  padding: 16px 20px;
  border-radius: 8px;
  border: 1px solid rgb(255 255 255 / 8%);
  background: linear-gradient(180deg, rgb(30 41 59 / 80%) 0%, rgb(15 23 42 / 90%) 100%);
  &--ok { border-left: 3px solid #10b981; }
  &--warning { border-left: 3px solid #f59e0b; }
  &--alert { border-left: 3px solid #f43f5e; }
}
.kpi-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.kpi-card__key {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgb(255 255 255 / 10%);
  color: #cbd5e1;
}
.kpi-card__name { font-size: 13px; color: #cbd5e1; }
.kpi-card__status { margin-left: auto; font-size: 12px; font-weight: 600; }
.kpi-card__value-row { margin-bottom: 6px; }
.kpi-card__value { font-size: 28px; font-weight: 800; }
.kpi-card__unit { font-size: 13px; color: #8a9aa9; margin-left: 4px; }
.kpi-card__target { font-size: 12px; color: #8a9aa9; margin-bottom: 4px;
  .label { color: #64748b; }
}
.kpi-card__detail { font-size: 11px; color: #64748b; }

// ═══ 图表网格 ═══
.chart-grid {
  display: grid;
  gap: 12px;
  &--2col {
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: 1fr;
    flex: 1;
    min-height: 0;
  }
}
:deep(.el-card) {
  background: linear-gradient(180deg, rgb(30 41 59 / 80%) 0%, rgb(15 23 42 / 90%) 100%);
  border: 1px solid rgb(255 255 255 / 8%);
  color: #e2e8f0;
}
:deep(.el-card__header) {
  border-bottom: 1px solid rgb(255 255 255 / 10%);
  color: #f1f5f9;
  font-size: 14px;
}
:deep(.el-card__body) {
  padding: 12px 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
:deep(.chart) { width: 100% !important; flex: 1; min-height: 0; }

// ═══ 数据表格 ═══
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  th {
    padding: 8px 10px;
    border-bottom: 2px solid rgb(255 255 255 / 10%);
    color: #8a9aa9;
    font-weight: 600;
    text-align: left;
    white-space: nowrap;
  }
  td {
    padding: 7px 10px;
    border-bottom: 1px solid rgb(255 255 255 / 6%);
    color: #cbd5e1;
    &.num { text-align: right; font-variant-numeric: tabular-nums; }
  }
  tr.row-alert { background: rgb(244 63 94 / 6%); }
}
.ellipsis-text { display: block; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-badge {
  display: inline-block;
  width: 22px;
  height: 22px;
  line-height: 22px;
  border-radius: 50%;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  color: #cbd5e1;
  background: rgb(255 255 255 / 8%);
  &.rank-1 { background: #f59e0b; color: #000; }
  &.rank-2 { background: #94a3b8; color: #000; }
  &.rank-3 { background: #cd853f; color: #fff; }
}
.ratio-bar {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: rgb(255 255 255 / 6%);
  overflow: hidden;
  &__fill { height: 100%; border-radius: 3px; background: #3b82f6; }
}
.mini-table {
  width: 100%;
  font-size: 13px;
  border-collapse: collapse;
  color: #e2e8f0;
  td {
    padding: 6px 8px;
    border-bottom: 1px solid rgb(255 255 255 / 6%);
  }
  .num { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
}
.action-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  &--red { background: rgb(244 63 94 / 20%); color: #f87171; }
  &--amber { background: rgb(245 158 11 / 20%); color: #fbbf24; }
  &--green { background: rgb(16 185 129 / 20%); color: #34d399; }
}
code {
  padding: 1px 5px;
  border-radius: 3px;
  background: rgb(255 255 255 / 6%);
  font-size: 11px;
  color: #a5b4fc;
}
</style>
