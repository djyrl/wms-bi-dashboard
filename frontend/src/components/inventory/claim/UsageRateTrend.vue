<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { UsageRatePoint } from '@/types/inventory'

const props = defineProps<{
  data: UsageRatePoint[]
  months: string[]
  granularity?: string
}>()

const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const timeLabel = computed(() => props.granularity || '周')
const detailHeaders = computed(() => [timeLabel.value, '领用率(%)', '目标(%)', '趋势值(%)'])
const detailRows = computed(() => props.data.map(d => [d.month, d.rate, d.target, d.trend] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const rates = props.data.map(d => d.rate)
  const trends = props.data.map(d => d.trend)
  const targets = props.data.map(d => d.target)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8', fontSize: 10 }, data: ['领用率', '趋势线', '目标线(20%)'] },
    grid: { top: 45, right: 55, bottom: 30, left: 55 },
    xAxis: { type: 'category', data: props.months, axisLabel: { color: '#cbd5e1', fontSize: 10, rotate: 45, interval: (props.months.length > 12 ? 'auto' : 0) }, axisLine: { lineStyle: { color: '#475569' } } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#94a3b8', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      {
        name: '领用率', type: 'line', data: rates, smooth: true,
        lineStyle: { color: '#f43f5e', width: 2.5 }, itemStyle: { color: '#f43f5e' }, symbol: 'circle', symbolSize: 6,
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(244,63,94,0.25)' }, { offset: 1, color: 'rgba(244,63,94,0)' }] } },
        markLine: { silent: true, symbol: 'none', data: [{ yAxis: 15, label: { formatter: '预警线 15%', color: '#f59e0b' }, lineStyle: { color: '#f59e0b', type: 'dashed', width: 1.5 } }] },
      },
      { name: '趋势线', type: 'line', data: trends, lineStyle: { color: '#facc15', width: 4, type: 'solid' }, itemStyle: { color: '#facc15' }, symbol: 'diamond', symbolSize: 10, z: 10, endLabel: { show: true, formatter: '趋势', color: '#facc15', fontSize: 13, fontWeight: 'bold', distance: 10 } },
      { name: '目标线(20%)', type: 'line', data: targets, lineStyle: { color: '#10b981', width: 1.5, type: 'dashed' }, itemStyle: { color: '#10b981' }, symbol: 'none' },
    ],
  })
}

onMounted(render)
watch([() => props.data, () => props.months], render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 280px; }
</style>
