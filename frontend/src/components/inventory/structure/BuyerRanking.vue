<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { BuyerRankItem } from '@/types/inventory'

const props = defineProps<{ data: BuyerRankItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['采购人', '库存(万)', '领用率(%)']
const detailRows = computed(() => props.data.map(d => [d.name, d.value, d.usageRate] as (string | number)[]))

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = props.data.map(d => d.name)
  const values = props.data.map(d => d.value)
  const rates = props.data.map(d => d.usageRate)

  chart.setOption({
    tooltip: { formatter: (p: { name: string; value: number; dataIndex: number }) => `${p.name}<br/>库存: <b>¥${p.value}万</b><br/>领用率: ${rates[p.dataIndex]}%` },
    grid: { top: 10, right: 60, bottom: 20, left: 100 },
    xAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 11 }, inverse: true },
    series: [{
      type: 'bar', data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: rates[i] < 60 ? '#f43f5e' : rates[i] < 75 ? '#f59e0b' : '#10b981', borderRadius: [0, 6, 6, 0] },
      })),
      barWidth: 18,
      label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: '{c}万' },
    }],
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
