<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { UsageRatePoint } from '@/types/inventory'

const props = defineProps<{
  data: UsageRatePoint[]
  months: string[]
  granularity?: string
  hideDetail?: boolean
}>()

const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const timeLabel = computed(() => props.granularity || '周')

// 格式化短标签（去掉年份，只显示月日）
const shortLabels = computed(() => props.months.map(m => {
  // "2026-05-11 ~ 2026-05-17" → "05-11~05-17"
  if (m.includes(' ~ ')) return m.replace(/\d{4}-(\d{2}-\d{2}) ~ \d{4}-(\d{2}-\d{2})/, '$1~$2')
  // "2026-01-15" → "01-15"
  if (m.length === 10) return m.slice(5)
  // "2026-W01" → "W01", "2026-01" → "01月"
  if (m.includes('W') || m.includes('w')) return m.replace(/^\d{4}-?/, '')
  if (m.length === 7) return m.slice(5) + '月'
  return m
}))

const detailHeaders = computed(() => [timeLabel.value, '领用率(%)', '目标(%)', '趋势值(%)'])
const detailRows = computed(() => [...props.data].reverse().map(d => [d.month, d.rate, d.target, d.trend] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const rates = props.data.map(d => d.rate)
  const trends = props.data.map(d => d.trend)
  const targets = props.data.map(d => d.target)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8', fontSize: 10 }, data: ['领用率', '趋势线', '目标线(20%)'] },
    grid: { top: 45, right: 55, bottom: 40, left: 55 },
    xAxis: { type: 'category', data: shortLabels.value, axisLabel: { color: '#cbd5e1', fontSize: 10, rotate: 45, interval: (props.months.length > 12 ? 'auto' : 0) }, axisLine: { lineStyle: { color: '#475569' } } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#94a3b8', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      {
        name: '领用率', type: 'line', data: rates, smooth: true,
        lineStyle: { color: '#10b981', width: 2.5 }, itemStyle: { color: '#10b981' }, symbol: 'circle', symbolSize: 6,
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(16,185,129,0.25)' }, { offset: 1, color: 'rgba(16,185,129,0)' }] } },
        markLine: { silent: true, symbol: 'none', data: [{ yAxis: 15, label: { formatter: '预警线 15%', color: '#ef4444' }, lineStyle: { color: '#ef4444', type: 'dashed', width: 1.5 } }] },
      },
      { name: '趋势线', type: 'line', data: trends, lineStyle: { color: '#3b82f6', width: 4, type: 'solid' }, itemStyle: { color: '#3b82f6' }, symbol: 'diamond', symbolSize: 10, z: 10, endLabel: { show: true, formatter: '趋势', color: '#3b82f6', fontSize: 13, fontWeight: 'bold', distance: 10 } },
      { name: '目标线(20%)', type: 'line', data: targets, lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' }, itemStyle: { color: '#f59e0b' }, symbol: 'none' },
    ],
  })
}

onMounted(render)
watch([() => props.data, () => props.months], render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail v-if="!props.hideDetail" :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 280px; }
</style>
