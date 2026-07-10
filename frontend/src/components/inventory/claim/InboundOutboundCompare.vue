<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { InOutPoint } from '@/types/inventory'

const props = defineProps<{ data: InOutPoint[]; months: string[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['周', '入库(万)', '领用(万)', '净增(万)']
const detailRows = computed(() => props.data.map(d => [d.month, d.inbound, d.outbound, d.net] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)
  const inbound = props.data.map(d => d.inbound)
  const outbound = props.data.map(d => d.outbound)
  const net = props.data.map(d => d.net)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8' }, data: ['入库金额', '领用金额', '净增库存'] },
    grid: { top: 40, right: 20, bottom: 20, left: 55 },
    xAxis: { type: 'category', data: props.months, axisLabel: { color: '#94a3b8', fontSize: 10 } },
    yAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
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
