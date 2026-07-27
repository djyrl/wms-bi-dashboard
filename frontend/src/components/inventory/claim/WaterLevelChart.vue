<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { WaterLevelItem } from '@/types/inventory'

const props = defineProps<{ data: WaterLevelItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

function toWan(v: number) { return +(v / 10000).toFixed(2) }

const detailHeaders = ['物料编码', '物料名称', '当前库存(万)', '安全上限(万)', '安全下限(万)', '状态']
const detailRows = computed(() =>
  props.data.map(d => {
    const status = d.current > d.safeMax ? '⚠ 超限' : d.current < d.safeMin ? '⚠ 不足' : '✅ 正常'
    return [d.materialCode, d.category, toWan(d.current), toWan(d.safeMax), toWan(d.safeMin), status] as (string | number)[]
  })
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const categories = props.data.map(d => d.category)
  const current = props.data.map(d => toWan(d.current))
  const safeMax = props.data.map(d => toWan(d.safeMax))
  const safeMin = props.data.map(d => toWan(d.safeMin))

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8' }, data: ['当前库存', '安全上限', '安全下限'] },
    grid: { top: 40, right: 20, bottom: 20, left: 55 },
    xAxis: { type: 'category', data: categories, axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 30 } },
    yAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '当前库存', type: 'bar', data: current.map((v, i) => ({ value: v, itemStyle: { color: v > safeMax[i] ? '#f43f5e' : '#3b82f6' } })), barWidth: 14 },
      { name: '安全上限', type: 'line', data: safeMax, lineStyle: { color: '#f43f5e', width: 1, type: 'dashed' }, symbol: 'none' },
      { name: '安全下限', type: 'line', data: safeMin, lineStyle: { color: '#f59e0b', width: 1, type: 'dashed' }, symbol: 'none' },
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
