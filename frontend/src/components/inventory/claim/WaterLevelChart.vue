<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { WaterLevelItem } from '@/types/inventory'

const props = defineProps<{ data: WaterLevelItem[]; hideDetail?: boolean }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

function toWan(v: number) { return +(v / 10000).toFixed(2) }

/** 截断横坐标标签：只保留物料名称 */
function shortName(name: string): string {
  if (!name) return ''
  // 取第一个分隔符（下划线、空格、中文破折号等）之前的部分作为物料名
  const sep = name.search(/[_ \-—，,（(]/)
  const base = sep > 0 ? name.slice(0, sep) : name
  return base.length > 8 ? base.slice(0, 8) + '…' : base
}

const detailHeaders = ['物料编码', '物料名称', '当前库存(万)', '安全上限(万)', '安全下限(万)', '状态']
const detailRows = computed(() =>
  props.data.map(d => {
    const status = d.current > d.safeMax ? '⚠ 超限' : d.current < d.safeMin ? '⚠ 不足' : '✅ 正常'
    return [d.materialCode, d.category, toWan(d.current), toWan(d.safeMax), toWan(d.safeMin), status] as (string | number)[]
  })
)

function render() {
  if (!chartRef.value || !props.data.length) return
  if (!chart.instance) chart.init(chartRef.value)

  const fullNames = props.data.map(d => d.category)
  const categories = props.data.map(d => shortName(d.category))
  const current = props.data.map(d => toWan(d.current))
  const safeMax = props.data.map(d => toWan(d.safeMax))
  const safeMin = props.data.map(d => toWan(d.safeMin))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        const idx = params[0]?.dataIndex ?? 0
        const name = fullNames[idx] || ''
        let html = `<b>${name}</b><br/>`
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${p.value} 万<br/>`
        })
        return html
      },
    },
    legend: { top: 0, textStyle: { color: '#94a3b8' }, data: ['当前库存', '安全上限', '安全下限'] },
    grid: { top: 40, right: 20, bottom: 20, left: 55 },
    xAxis: { type: 'category', data: categories, axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 30 } },
    yAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '当前库存', type: 'bar', data: current.map((v, i) => ({ value: v, itemStyle: { color: v > safeMax[i] ? '#f43f5e' : '#3b82f6' } })), barWidth: 14 },
      { name: '安全上限', type: 'line', data: safeMax, lineStyle: { color: '#f43f5e', width: 1, type: 'dashed' }, symbol: 'none' },
      { name: '安全下限', type: 'line', data: safeMin, lineStyle: { color: '#f59e0b', width: 1, type: 'dashed' }, symbol: 'none' },
    ],
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
.chart { width: 100%; height: 280px; }
</style>
