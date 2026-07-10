<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { OverstockItem } from '@/types/inventory'

const props = defineProps<{ data: OverstockItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['物料', '当前库存(万)', '安全上限(万)', '超标倍数']
const detailRows = computed(() =>
  props.data.map(d => [d.name, d.current, d.safeMax, (d.current / d.safeMax).toFixed(1) + 'x'] as (string | number)[])
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = props.data.map(d => d.name)
  const current = props.data.map(d => d.current)
  const safeMax = props.data.map(d => d.safeMax)
  const ratio = props.data.map(d => +(d.current / d.safeMax).toFixed(1))

  chart.setOption({
    tooltip: { formatter: (p: { name: string; dataIndex: number }) => `${p.name}<br/>当前库存: <b>¥${current[p.dataIndex]}万</b><br/>安全上限: ¥${safeMax[p.dataIndex]}万<br/>超标倍数: <b>${ratio[p.dataIndex]}x</b>` },
    grid: { top: 5, right: 30, bottom: 20, left: 130 },
    xAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 10, width: 120, overflow: 'truncate' }, inverse: true },
    series: [
      { name: '安全上限', type: 'bar', data: safeMax, itemStyle: { color: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.15)', borderWidth: 1 }, barWidth: 12, barGap: '-100%', z: 1 },
      { name: '当前库存', type: 'bar', data: current.map((v, i) => ({ value: v, itemStyle: { color: ratio[i] > 2.5 ? '#f43f5e' : '#f59e0b', borderRadius: [0, 5, 5, 0] } })), barWidth: 12, z: 2, label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: (p: { dataIndex: number }) => `${ratio[p.dataIndex]}x` } },
    ],
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
.chart { width: 100%; height: 280px; }
</style>
