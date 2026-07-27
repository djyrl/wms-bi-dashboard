<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { OptimizeSuggestItem } from '@/types/inventory'

const props = defineProps<{ data: OptimizeSuggestItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()
const renderKey = ref(0)

const detailHeaders = ['物料', '当前库存(万)', '建议上限(万)', '日均消耗(万)']
const detailRows = computed(() =>
  props.data.map(d => [d.name, d.current, d.maxStock, d.dailyUse] as (string | number)[])
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = props.data.map(d => d.name)
  const current = props.data.map(d => d.current)
  const maxStock = props.data.map(d => d.maxStock)
  const dailyUse = props.data.map(d => d.dailyUse)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(params: any[]) {
        let html = `${params[0].axisValue}<br/>`
        params.forEach((p: any) => {
          if (p.seriesName === '日均消耗') {
            html += `${p.marker} ${p.seriesName}: ${(p.value * 10000).toLocaleString()} 元/天<br/>`
          } else {
            html += `${p.marker} ${p.seriesName}: ${p.value} 万元<br/>`
          }
        })
        return html
      },
    },
    legend: { top: 0, textStyle: { color: '#94a3b8', fontSize: 10 }, data: ['当前库存(万元)', '建议上限(万元)', '日均消耗(元/天)'] },
    grid: { top: 40, right: 65, bottom: 20, left: 55 },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 25 } },
    yAxis: [
      { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
      {
        type: 'value', name: '元/天', nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8', formatter(v: number) { return (v * 10000).toLocaleString() } },
        splitLine: { show: false },
      },
    ],
    series: [
      { name: '当前库存', type: 'bar', data: current, itemStyle: { color: '#f59e0b', borderRadius: [6, 6, 0, 0] }, barWidth: 18, barGap: '30%' },
      { name: '建议上限', type: 'bar', data: maxStock, itemStyle: { color: '#10b981', borderRadius: [6, 6, 0, 0] }, barWidth: 18 },
      { name: '日均消耗', type: 'line', yAxisIndex: 1, data: dailyUse, lineStyle: { color: '#06b6d4', width: 1.5 }, itemStyle: { color: '#06b6d4' }, symbol: 'circle', symbolSize: 5 },
    ],
  })
}

onMounted(() => { nextTick(render) })
watch(() => [props.data, renderKey.value], () => { nextTick(render) }, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 280px; }
</style>
