<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useDashboardStore } from '@/stores/modules/dashboard'
import { storeToRefs } from 'pinia'
import { useECharts } from '@/composables/useECharts'
import type { EChartsOption } from 'echarts'

const store = useDashboardStore()
const { claim } = storeToRefs(store)
const { init, setOption, resize, dispose } = useECharts()
const chartRef = ref<HTMLDivElement>()

function buildOption(rateAmount: number, rateQty: number): EChartsOption {
  return {
    series: [
      {
        type: 'gauge' as const, center: ['25%', '55%'], radius: '80%',
        startAngle: 200, endAngle: -20,
        min: 0, max: 100,
        splitNumber: 10,
        axisLine: { show: true, lineStyle: { width: 12, color: [[0.8, '#10b981'], [0.5, '#f59e0b'], [1, '#ef4444']] } },
        pointer: { length: '60%', width: 6, itemStyle: { color: 'auto' } },
        detail: { valueAnimation: true, formatter: '{value}%', fontSize: 16, offsetCenter: [0, '70%'] },
        title: { offsetCenter: [0, '90%'], fontSize: 11 },
        data: [{ value: rateAmount, name: '金额领用率' }],
      },
      {
        type: 'gauge' as const, center: ['75%', '55%'], radius: '80%',
        startAngle: 200, endAngle: -20,
        min: 0, max: 100,
        splitNumber: 10,
        axisLine: { show: true, lineStyle: { width: 12, color: [[0.8, '#10b981'], [0.5, '#f59e0b'], [1, '#ef4444']] } },
        pointer: { length: '60%', width: 6, itemStyle: { color: 'auto' } },
        detail: { valueAnimation: true, formatter: '{value}%', fontSize: 16, offsetCenter: [0, '70%'] },
        title: { offsetCenter: [0, '90%'], fontSize: 11 },
        data: [{ value: rateQty, name: '数量领用率' }],
      },
    ],
  } as EChartsOption
}

watch(() => claim.value, (c) => {
  if (c) nextTick(() => setOption(buildOption(c.claim_rate_amount, c.claim_rate_quantity)))
}, { deep: true })

onMounted(() => {
  if (chartRef.value) {
    init(chartRef.value)
    if (claim.value) setOption(buildOption(claim.value.claim_rate_amount, claim.value.claim_rate_quantity))
  }
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => { window.removeEventListener('resize', resize); dispose() })
</script>

<template>
  <div ref="chartRef" class="chart-box" />
</template>
