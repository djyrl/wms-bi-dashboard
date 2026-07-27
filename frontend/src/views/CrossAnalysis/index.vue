<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'
import { getTopProjects } from '@/api/modules/crossAnalysis'
import request from '@/api/request'
import type { KpiCardData } from '@/types/inventory'
import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'
import CrossBarChart from '@/components/inventory/cross/CrossBarChart.vue'

interface Dimension { label: string; value: string; type: string }
interface FilterRow { id: number; field: string; value: string | null; options: string[] }
let nextId = 1

const loading = ref(false)
const error = ref<string | null>(null)
const dimensions = ref<Dimension[]>([])
const xAxis = ref('month')
const yAxis = ref('inventory_amount')
const timeUnit = ref('month')
const filters = ref<FilterRow[]>([])
const barLabels = ref<string[]>([])
const barValues = ref<number[]>([])
const barUnit = ref('万元')

const allDims = computed(() => dimensions.value.filter(d => d.value !== 'week'))
const xOptions = computed(() => allDims.value.filter(d => d.type !== 'metric'))
const yOptions = computed(() => allDims.value.filter(d => d.type === 'metric'))
const usedFields = computed(() => {
  const s = new Set<string>([xAxis.value, yAxis.value])
  filters.value.forEach(f => { if (f.field) s.add(f.field) })
  return s
})
const filterAvailableDims = computed(() => allDims.value.filter(d => d.type !== 'metric' && !usedFields.value.has(d.value)))

const xLabel = computed(() => {
  if (xAxis.value === 'month' || xAxis.value === 'week') return `时间(${{ day: '天', week: '周', month: '月', year: '年' }[timeUnit.value]})`
  return allDims.value.find(d => d.value === xAxis.value)?.label || xAxis.value
})
const yLabel = computed(() => allDims.value.find(d => d.value === yAxis.value)?.label || yAxis.value)

const kpiCards = computed<KpiCardData[]>(() => [
  { icon: '📊', label: '横轴', value: 0, unit: xLabel.value, change: `${barLabels.value.length} 项`, changeType: 'up', color: '#3b82f6' },
  { icon: '📈', label: '纵轴', value: 0, unit: yLabel.value, change: `合计 ${barValues.value.reduce((a,b)=>a+b,0).toFixed(0)} ${barUnit.value}`, changeType: 'up', color: '#f59e0b' },
  { icon: '🔍', label: '筛选', value: filters.value.length, unit: '个', change: `${filterAvailableDims.value.length} 维度可用`, changeType: 'up', color: '#8b5cf6' },
  { icon: '📉', label: '粒度', value: 0, unit: timeUnit.value === 'month' ? '月' : timeUnit.value, change: '时间聚合粒度', changeType: 'up', color: '#10b981' },
])

function addFilter() {
  const avail = filterAvailableDims.value
  if (!avail.length) return
  filters.value.push({ id: nextId++, field: '', value: null, options: [] })
}
function removeFilter(id: number) {
  filters.value = filters.value.filter(f => f.id !== id)
  loadData()
}

async function onFilterFieldChange(id: number, field: string) {
  const idx = filters.value.findIndex(f => f.id === id)
  if (idx < 0) return
  if (field === 'month' || field === 'week') {
    filters.value[idx] = { id, field, value: 'month', options: ['天', '周', '月', '年'] }
    return
  }
  const apiField = ({ purchaser: 'purchaser_name' } as Record<string, string>)[field] || field
  try {
    const opts = await request.get<string[]>('/wms/indicators/distinct-values', { params: { field: apiField } })
    filters.value[idx] = { id, field, value: null, options: opts }
  } catch {
    filters.value[idx] = { id, field, value: null, options: [] }
  }
}
function onFilterValueChange() { loadData() }

async function loadData() {
  loading.value = true
  error.value = null
  const groupBy = xAxis.value === 'time' ? timeUnit.value : xAxis.value
  try {
    const pt = filters.value.find(f => f.field === 'project_type' && f.value)?.value || undefined
    const bar = await getTopProjects({ metric: yAxis.value, project_type: pt, limit: 15, group_by: groupBy })
    barLabels.value = bar.labels
    barValues.value = bar.values
    barUnit.value = bar.unit
  } catch (e: any) {
    error.value = e.message || '加载失败'
  }
  loading.value = false
}

async function init() {
  try {
    dimensions.value = await request.get<Dimension[]>('/wms/indicators/available-dimensions')
  } catch {}
  loadData()
}

onMounted(() => init())
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载分析数据..." class="cross-analysis-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="init()" />
    <template v-if="!error">
      <KpiCards :cards="kpiCards" />

      <div class="axis-bar">
        <span class="axis-label">横轴</span>
        <el-select v-model="xAxis" size="small" style="width: 140px" @change="loadData()">
          <el-option v-for="d in xOptions" :key="d.value" :label="d.label" :value="d.value" />
        </el-select>
        <template v-if="xAxis === 'month' || xAxis === 'week'">
          <el-radio-group v-model="timeUnit" size="small" @change="loadData()">
            <el-radio-button value="day">天</el-radio-button>
            <el-radio-button value="week">周</el-radio-button>
            <el-radio-button value="month">月</el-radio-button>
            <el-radio-button value="year">年</el-radio-button>
          </el-radio-group>
        </template>
        <span class="axis-label">×</span>
        <span class="axis-label">纵轴</span>
        <el-select v-model="yAxis" size="small" style="width: 160px" @change="loadData()">
          <el-option v-for="d in yOptions" :key="d.value" :label="d.label" :value="d.value" />
        </el-select>
        <el-button type="primary" size="small" @click="loadData()">更新图表</el-button>
      </div>

      <div class="filter-section">
        <div class="filter-row" v-for="f in filters" :key="f.id">
          <el-select
            v-model="f.field"
            placeholder="选择维度"
            size="small"
            style="width: 130px"
            @change="(v: string) => onFilterFieldChange(f.id, v)"
          >
            <el-option v-for="d in filterAvailableDims" :key="d.value" :label="d.label" :value="d.value" />
          </el-select>
        <span>:</span>
        <el-select
          v-model="f.value"
          placeholder="全部"
          size="small"
          style="width: 220px"
          clearable
          :disabled="!f.field"
          @change="onFilterValueChange()"
        >
          <el-option v-for="opt in f.options" :key="opt" :label="opt" :value="opt" />
        </el-select>
        <el-button size="small" text type="danger" @click="removeFilter(f.id)"><el-icon><Delete /></el-icon></el-button>
      </div>
      <el-button size="small" text type="primary" :disabled="!filterAvailableDims.length" @click="addFilter"><el-icon><Plus /></el-icon> 添加筛选维度</el-button>
    </div>

    <ChartCard :title="'📊 ' + yLabel + ' 对比'">
      <template #actions><span class="card-subtitle">TOP 15 按 {{ xLabel }} 维度</span></template>
      <CrossBarChart v-if="barLabels.length" :labels="barLabels" :values="barValues" :unit="barUnit" />
    </ChartCard>
  </template>
</div>
</template>

<style lang="scss" scoped>
.cross-analysis-dashboard { padding: 0 0 24px; }
.axis-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.axis-label { font-size: 15px; font-weight: 600; }
.filter-section { margin-bottom: 12px; }
.filter-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.card-subtitle { font-size: 11px; }
</style>
