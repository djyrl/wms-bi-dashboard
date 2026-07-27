<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useECharts } from '@/composables/useECharts'

const props = defineProps<{
  labels: string[]
  values: number[]
  unit: string
}>()

const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

function render() {
  if (!chartRef.value || !props.labels.length) return
  chart.init(chartRef.value)

  chart.setOption({
    backgroundColor: '#0f172a',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p: { name: string; value: number }[]) => {
        const item = p[0]
        return `${item.name}<br/><b>${item.value} ${props.unit}</b>`
      },
    },
    grid: { top: 20, right: 20, bottom: 30, left: 120 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    yAxis: {
      type: 'category',
      data: props.labels,
      axisLabel: { color: '#94a3b8' },
      axisLine: { lineStyle: { color: '#1e293b' } },
    },
    series: [
      {
        type: 'bar',
        data: props.values,
        itemStyle: { color: '#3b82f6', borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 24,
      },
    ],
  })
}

onMounted(render)
watch(
  () => [props.labels, props.values],
  render,
  { deep: true },
)
</script>

<template>
  <div ref="chartRef" class="chart" />
</template>

<style lang="scss" scoped>
.chart {
  width: 100%;
  height: 350px;
}
</style>
