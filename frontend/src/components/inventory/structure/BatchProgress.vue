<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { BatchDigestItem } from '@/types/inventory'

const props = defineProps<{ data: BatchDigestItem[]; labels: string[]; hideDetail?: boolean }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const validData = computed(() => props.data.filter(d => d.name != null && d.data != null && d.color != null))

const detailHeaders = computed(() => ['批次', ...props.labels])
const detailRows = computed(() => validData.value.map(d => [d.name, ...d.data.map(v => v + '%')] as (string | number)[]))

function render() {
  if (!chartRef.value || !validData.value.length) return
  chart.init(chartRef.value)

  chart.setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => v + '%' },
    legend: { top: 0, textStyle: { color: '#94a3b8', fontSize: 10 }, data: validData.value.map(d => d.name) },
    grid: { top: 40, right: 20, bottom: 20, left: 55 },
    xAxis: { type: 'category', data: props.labels, axisLabel: { color: '#94a3b8', fontSize: 10 } },
    yAxis: { type: 'value', name: '剩余占比 %', min: 0, max: 100, nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: validData.value.map(d => ({
      name: d.name, type: 'line', data: d.data, smooth: true,
      lineStyle: { color: d.color, width: 2 },
      itemStyle: { color: d.color },
    })),
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail v-if="!props.hideDetail" :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 300px; }
</style>
