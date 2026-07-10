<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { AgePyramidItem } from '@/types/inventory'

const props = defineProps<{ data: AgePyramidItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['库龄段', '库存金额(万)', 'SKU数']
const detailRows = computed(() => props.data.map(d => [d.range, d.amount, d.skuCount] as (string | number)[]))

const barColors = ['#10b981', '#06b6d4', '#3b82f6', '#f59e0b', '#8b5cf6', '#f43f5e']

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const labels = props.data.map(d => d.range)
  const amounts = props.data.map(d => d.amount)
  const skus = props.data.map(d => d.skuCount)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8' }, data: ['库存金额(万)', 'SKU数'] },
    grid: { top: 40, right: 55, bottom: 20, left: 65 },
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: labels, axisLabel: { color: '#94a3b8', fontSize: 11 } },
    series: [
      { name: '库存金额(万)', type: 'bar', data: amounts.map((v, i) => ({ value: v, itemStyle: { color: barColors[i] } })), barWidth: 14, barGap: '40%', label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: '{c}万' } },
      { name: 'SKU数', type: 'bar', data: skus.map(v => v / 10), itemStyle: { color: 'rgba(255,255,255,0.08)', borderColor: 'rgba(255,255,255,0.2)', borderWidth: 1 }, barWidth: 14, label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: (p: { value: number }) => `${(p.value * 10)}个` } },
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
.chart { width: 100%; height: 300px; }
</style>
