<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { AnomalyDay } from '@/types/inventory'

const props = defineProps<{ data: AnomalyDay[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['日期', '状态']
const detailRows = computed(() => props.data.map(d => [d.date, d.label] as (string | number)[]))

const anomalyLabels = ['✅ 正常', '⚠️ 领用异常']

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const days = props.data.map(d => d.date)
  const values = props.data.map((d, i) => [i, 0, d.type])

  chart.setOption({
    tooltip: { formatter: (p: { name: string; value: number[] }) => `${p.name}<br/>${anomalyLabels[p.value[2]]}` },
    grid: { top: 10, right: 20, bottom: 20, left: 20 },
    xAxis: { type: 'category', data: days, axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 60 }, axisTick: { show: false } },
    yAxis: { type: 'category', data: ['异常类型'], axisLabel: { color: '#94a3b8' }, axisLine: { show: false }, axisTick: { show: false } },
    visualMap: { show: false, pieces: [{ value: 0, color: '#1e293b' }, { value: 1, color: '#f59e0b' }] },
    series: [{
      type: 'heatmap', data: values,
      label: { show: true, fontSize: 9, formatter: (p: { value: number[] }) => ['✅', '⚠️'][p.value[2]], color: (p: { value: number[] }) => p.value[2] === 0 ? 'rgba(255,255,255,0.25)' : '#fff' },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(255,255,255,0.3)' } },
    }],
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
