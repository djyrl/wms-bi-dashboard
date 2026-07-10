<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useDashboardStore } from '@/stores/modules/dashboard'
import { storeToRefs } from 'pinia'
import { useECharts } from '@/composables/useECharts'
import { formatAmount } from '@/utils/format'
import type { EChartsOption } from 'echarts'
import type { AgeStructureItem } from '@/types/dashboard'

const store = useDashboardStore()
const { time } = storeToRefs(store)
const { init, setOption, resize, dispose } = useECharts()
const chartRef = ref<HTMLDivElement>()

const BAR_COLORS = ['#10b981', '#f59e0b', '#f97316', '#ef4444']

function buildOption(data: AgeStructureItem[]): EChartsOption {
  return {
    tooltip: { trigger: 'axis' as const, formatter: (p: unknown) => {
      const items = p as Array<{ name: string; value: number }>
      return items.map(i => `${i.name}: ${formatAmount(i.value)}`).join('<br/>')
    }},
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: { type: 'category' as const, data: data.map(d => d.range) },
    yAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` } },
    series: [{
      type: 'bar' as const, barMaxWidth: 40,
      data: data.map((d, i) => ({
        value: d.amount,
        itemStyle: { color: BAR_COLORS[i] || '#6b7280', borderRadius: [4, 4, 0, 0] },
      })),
      label: { show: true, position: 'top' as const, formatter: (p: unknown) => {
        const item = p as { value: number }
        return `${((item.value / data.reduce((s, d) => s + d.amount, 0)) * 100).toFixed(1)}%`
      }},
    }],
  } as EChartsOption
}

watch(() => time.value?.age_structure, (data) => {
  if (data?.length) nextTick(() => setOption(buildOption(data)))
}, { deep: true })

onMounted(() => {
  if (chartRef.value) {
    init(chartRef.value)
    if (time.value?.age_structure.length) setOption(buildOption(time.value.age_structure))
  }
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => { window.removeEventListener('resize', resize); dispose() })
</script>

<template>
  <div ref="chartRef" class="chart-box" />
</template>
