<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import { formatDays } from '@/utils/format'
import type { AgeTrendPoint } from '@/types/inventory'

const props = defineProps<{ data: AgeTrendPoint[]; months: string[]; hideDetail?: boolean }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['月份', '平均库龄(天)', '趋势值(天)', '>90天占比(%)']
const detailRows = computed(() => props.data.map(d => [d.month, formatDays(d.avgAge), formatDays(d.trend), d.over90Rate.toFixed(1) + '%'] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const avgAges = props.data.map(d => d.avgAge)
  const trends = props.data.map(d => d.trend)
  const over90s = props.data.map(d => d.over90Rate)

  // 根据真实数据动态计算 Y 轴范围，留 15% 上下边距
  const ageMin = Math.floor(Math.min(...avgAges) * 0.85)
  const ageMax = Math.ceil(Math.max(...avgAges, ...trends) * 1.15)
  const rateMin = Math.floor(Math.min(...over90s) * 0.85)
  const rateMax = Math.ceil(Math.max(...over90s) * 1.15)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8' }, data: ['平均库龄(天)', '趋势线', '>90天占比(%)'] },
    grid: { top: 45, right: 55, bottom: 25, left: 55 },
    xAxis: { type: 'category', data: props.months, axisLabel: { color: '#94a3b8', fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '天', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }, min: ageMin, max: ageMax },
      { type: 'value', name: '%', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { show: false }, min: rateMin, max: rateMax },
    ],
    series: [
      { name: '平均库龄(天)', type: 'line', data: avgAges, smooth: true, lineStyle: { color: '#8b5cf6', width: 2.5 }, itemStyle: { color: '#8b5cf6' }, symbol: 'circle', symbolSize: 5, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(139,92,246,0.2)' }, { offset: 1, color: 'rgba(139,92,246,0)' }] } }, markLine: { silent: true, symbol: 'none', data: [{ yAxis: 45, label: { formatter: '警戒线 45天', color: '#f59e0b' }, lineStyle: { color: '#f59e0b', type: 'dashed' } }] } },
      { name: '趋势线', type: 'line', data: trends, lineStyle: { color: '#fbbf24', width: 2, type: 'dotted' }, itemStyle: { color: '#fbbf24' }, symbol: 'none', endLabel: { show: true, formatter: '↑ 上升趋势', color: '#fbbf24', fontSize: 11 } },
      { name: '>90天占比(%)', type: 'line', yAxisIndex: 1, data: over90s, smooth: true, lineStyle: { color: '#f43f5e', width: 2 }, itemStyle: { color: '#f43f5e' }, symbol: 'diamond', symbolSize: 5, markLine: { silent: true, symbol: 'none', data: [{ yAxis: 15, label: { formatter: '危险线 15%', color: '#f43f5e' }, lineStyle: { color: '#f43f5e', type: 'dashed' } }] } },
    ],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail v-if="!props.hideDetail" :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 300px; }
</style>
