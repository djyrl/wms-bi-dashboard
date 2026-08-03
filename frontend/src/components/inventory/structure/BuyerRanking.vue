<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { BuyerRankItem } from '@/types/inventory'

const props = defineProps<{ data: BuyerRankItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const TOP_N = 10
const displayData = computed(() => props.data.slice(0, TOP_N))

const detailHeaders = ['采购人', '库存(万)', '领用率(%)']
const detailRows = computed(() => props.data.map(d => [d.name, Number(d.value).toFixed(2), d.usageRate] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = displayData.value.map(d => d.name)
  const values = displayData.value.map(d => d.value)
  const rates = displayData.value.map(d => d.usageRate)

  chart.setOption({
    tooltip: { formatter: (p: { name: string; value: number; dataIndex: number }) => `${p.name}<br/>库存: <b>¥${Number(p.value).toFixed(2)}万</b><br/>领用率: ${rates[p.dataIndex]}%` },
    grid: { top: 4, right: 50, bottom: 16, left: 90, containLabel: true },
    xAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 11 }, inverse: true, axisLine: { show: false }, axisTick: { show: false } },
    series: [{
      type: 'bar', data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: rates[i] < 60 ? '#f43f5e' : rates[i] < 75 ? '#f59e0b' : '#10b981', borderRadius: [0, 6, 6, 0] },
      })),
      barMaxWidth: 20,
      label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: (p: { value: number }) => `${Number(p.value).toFixed(2)}万` },
    }],
  })
}

onMounted(render)
watch(displayData, render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 320px; }
</style>
