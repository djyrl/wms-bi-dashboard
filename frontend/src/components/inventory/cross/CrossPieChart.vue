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

const COLORS = [
  '#3b82f6',
  '#f59e0b',
  '#10b981',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#f97316',
  '#84cc16',
  '#14b8a6',
]

function render() {
  if (!chartRef.value || !props.labels.length) return
  chart.init(chartRef.value)

  const pieData = props.labels.map((name, i) => ({
    name,
    value: props.values[i] ?? 0,
  }))

  chart.setOption({
    backgroundColor: '#0f172a',
    tooltip: {
      trigger: 'item',
      formatter: (p: { name: string; value: number; percent: number }) =>
        `${p.name}<br/>${p.value} ${props.unit} (${p.percent}%)`,
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#94a3b8' },
    },
    grid: { top: 20, right: 80, bottom: 30, left: 60 },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '48%'],
        data: pieData,
        itemStyle: {
          borderColor: '#0f172a',
          borderWidth: 3,
          borderRadius: 4,
        },
        color: COLORS,
        label: {
          color: '#94a3b8',
          formatter: (p: { name: string; percent: number }) =>
            `${p.name}\n${p.percent}%`,
        },
        emphasis: {
          label: { fontSize: 16, fontWeight: 'bold' },
        },
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
