<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useECharts } from '@/composables/useECharts'

const props = defineProps<{
  data: number[][]
  projects: string[]
  months: string[]
  unit: string
}>()

const emit = defineEmits<{
  drill: [projectLabel: string]
}>()

const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const hmData: [number, number, number][] = []
  let maxVal = 0
  for (let y = 0; y < props.projects.length; y++) {
    for (let x = 0; x < props.months.length; x++) {
      const v = props.data[y]?.[x] ?? 0
      hmData.push([x, y, v])
      if (v > maxVal) maxVal = v
    }
  }

  chart.instance?.off('click')
  chart.instance?.on('click', (params: any) => {
    if (params.componentType === 'series' && params.data) {
      const yIdx = params.data[1]
      const label = props.projects[yIdx]
      if (label) emit('drill', label)
    }
  })

  chart.setOption({
    tooltip: {
      formatter: (p: { value: number[] }) =>
        `${props.projects[p.value[1]]} / ${props.months[p.value[0]]}<br/>${props.unit}: <b>${p.value[2]}</b>`,
    },
    grid: { top: 10, right: 20, bottom: 40, left: 100 },
    xAxis: {
      type: 'category', data: props.months,
      axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 45 },
      position: 'bottom',
    },
    yAxis: {
      type: 'category', data: props.projects,
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    visualMap: {
      right: 10, bottom: 50,
      min: 0, max: Math.ceil(maxVal * 1.1) || 10,
      inRange: { color: ['#111827', '#1e3a5f', '#2563eb', '#f59e0b', '#ef4444'] },
      text: ['高', '低'], textStyle: { color: '#94a3b8' },
    },
    series: [{
      type: 'heatmap', data: hmData,
      label: { show: true, color: '#fff', fontSize: 9 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  })
}

watch(() => [props.data, props.projects, props.months], () => nextTick(render), { deep: true })
</script>

<template>
  <div>
    <div ref="chartRef" class="cross-heatmap" />
    <div class="drill-hint">点击项目名称可下钻筛选</div>
  </div>
</template>

<style lang="scss" scoped>
.cross-heatmap {
  width: 100%;
  height: 420px;
}
.drill-hint {
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
  margin-top: 4px;
}
</style>
