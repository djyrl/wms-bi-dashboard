<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useECharts } from '@/composables/useECharts'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  data: { name: string; value: number }[]
  title?: string
  height?: string
  colors?: string[]
}>()

const { init, setOption, resize, dispose } = useECharts()
const chartRef = ref<HTMLDivElement>()

const DEFAULT_COLORS = ['#4f46e5','#38bdf8','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#64748b']

function buildOption(): EChartsOption {
  return {
    title: props.title ? { text: props.title, left: 'center', top: 0, textStyle: { fontSize: 13 } } : undefined,
    tooltip: { trigger: 'item' as const },
    legend: { bottom: 0, itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 10 } },
    series: [{
      type: 'pie' as const, radius: ['50%', '75%'], center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' as const } },
      data: props.data,
      color: props.colors || DEFAULT_COLORS,
    }],
  } as EChartsOption
}

onMounted(() => {
  if (chartRef.value) { init(chartRef.value); nextTick(() => setOption(buildOption())) }
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => { window.removeEventListener('resize', resize); dispose() })
</script>

<template>
  <div ref="chartRef" :style="{ height: height || '300px', width: '100%' }" />
</template>
