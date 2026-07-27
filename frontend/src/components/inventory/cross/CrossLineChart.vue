<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useECharts } from '@/composables/useECharts'

const props = defineProps<{
  months: string[]
  series: { name: string; data: number[] }[]
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
]

function render() {
  if (!chartRef.value || !props.months.length) return
  chart.init(chartRef.value)

  chart.setOption({
    backgroundColor: '#0f172a',
    tooltip: {
      trigger: 'axis',
      formatter: (params: { seriesName: string; value: number; axisValue?: string; color?: string }[]) => {
        let html = params[0]?.axisValue + '<br/>'
        params.forEach((p) => {
          html += `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:${p.color ?? 'transparent'}"></span>${p.seriesName}: <b>${p.value} ${props.unit}</b><br/>`
        })
        return html
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#94a3b8' },
    },
    grid: { top: 20, right: 80, bottom: 30, left: 60 },
    xAxis: {
      type: 'category',
      data: props.months,
      axisLabel: { color: '#94a3b8' },
      axisLine: { lineStyle: { color: '#1e293b' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    series: props.series.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: COLORS[i % COLORS.length], width: 2 },
      itemStyle: { color: COLORS[i % COLORS.length] },
    })),
  })
}

onMounted(render)
watch(
  () => [props.months, props.series],
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
