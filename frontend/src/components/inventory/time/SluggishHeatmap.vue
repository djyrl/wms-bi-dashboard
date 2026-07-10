<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'

const props = defineProps<{
  data: number[][]
  categories: string[]
  ageLabels: string[]
}>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = computed(() => ['物料类别', ...props.ageLabels.slice().reverse()])
const detailRows = computed(() =>
  props.categories.map((cat, x) => {
    const vals: number[] = []
    for (let y = props.ageLabels.length - 1; y >= 0; y--) {
      vals.push(props.data[y]?.[x] ?? 0)
    }
    return [cat, ...vals] as (string | number)[]
  })
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const hmData: [number, number, number][] = []
  const rowCount = props.data.length
  const colCount = props.categories.length
  let maxVal = 0
  for (let y = 0; y < rowCount; y++) {
    for (let x = 0; x < colCount; x++) {
      const v = props.data[y]?.[x] ?? 0
      hmData.push([x, y, v])
      if (v > maxVal) maxVal = v
    }
  }

  chart.setOption({
    tooltip: { formatter: (p: { value: number[] }) => `${props.ageLabels[p.value[1]]} / ${props.categories[p.value[0]]}<br/>库存: <b>¥${p.value[2]}万</b>` },
    grid: { top: 10, right: 20, bottom: 40, left: 75 },
    xAxis: { type: 'category', data: props.categories, axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 45 }, position: 'bottom' },
    yAxis: { type: 'category', data: props.ageLabels, axisLabel: { color: '#94a3b8', fontSize: 10 } },
    visualMap: { right: 10, bottom: 50, min: 0, max: Math.ceil(maxVal * 1.1) || 10, inRange: { color: ['#111827', '#1e3a5f', '#2563eb', '#f59e0b', '#ef4444'] }, text: ['高', '低'], textStyle: { color: '#94a3b8' } },
    series: [{ type: 'heatmap', data: hmData, label: { show: true, color: '#fff', fontSize: 9 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }],
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
