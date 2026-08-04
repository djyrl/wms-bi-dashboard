<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { InOutPoint } from '@/types/inventory'

const props = defineProps<{ data: InOutPoint[]; months: string[]; granularity?: string }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

function toWan(v: number) { return +(v / 10000).toFixed(2) }

const timeLabel = computed(() => props.granularity || '周')

const chartYear = computed(() => {
  const m = props.months[0]
  return m ? m.slice(0, 4) : ''
})
const shortLabels = computed(() => props.months.map(m => {
  if (m.length === 10) return m.slice(5)
  if (m.includes('W') || m.includes('w')) return m.replace(/^\d{4}-?/, '')
  if (m.length === 7) return m.slice(5) + '月'
  return m
}))

const detailHeaders = computed(() => [timeLabel.value, '入库(万)', '领用(万)', '净增(万)'])
const detailRows = computed(() => props.data.map(d => [d.month, toWan(d.inbound), toWan(d.outbound), toWan(d.net)] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)
  const inbound = props.data.map(d => toWan(d.inbound))
  const outbound = props.data.map(d => toWan(d.outbound))
  const net = props.data.map(d => toWan(d.net))

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8' }, data: ['入库金额', '领用金额', '净增库存'] },
    grid: { top: 40, right: 20, bottom: 40, left: 55 },
    xAxis: { type: 'category', data: shortLabels.value, axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 45, interval: (props.months.length > 12 ? 'auto' : 0) } },
    yAxis: { type: 'value', name: chartYear.value + ' 万元', nameLocation: 'end', nameTextStyle: { color: '#64748b', fontSize: 18, fontWeight: 'bold' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '入库金额', type: 'bar', data: inbound, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#3b82f6' }, { offset: 1, color: 'rgba(59,130,246,0.2)' }] } }, barWidth: 16, barGap: '30%' },
      { name: '领用金额', type: 'bar', data: outbound, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#06b6d4' }, { offset: 1, color: 'rgba(6,182,212,0.2)' }] } }, barWidth: 16 },
      { name: '净增库存', type: 'line', data: net, smooth: true, lineStyle: { color: '#f59e0b', width: 2 }, itemStyle: { color: '#f59e0b' }, symbol: 'triangle', symbolSize: 8, markLine: { silent: true, symbol: 'none', data: [{ yAxis: 0, label: { formatter: '平衡线' }, lineStyle: { color: 'rgba(255,255,255,0.3)' } }] } },
    ],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 280px; }
</style>
