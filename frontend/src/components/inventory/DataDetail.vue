<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  headers: string[]
  rows: (string | number)[][]
}>()

// 根据第一行数据，推断每列的语义类型
const colStyle = computed(() => {
  const styles: Record<string, string>[] = []
  if (props.rows.length === 0) return styles
  const firstRow = props.rows[0]
  for (let i = 0; i < props.headers.length; i++) {
    const isNum = typeof firstRow[i] === 'number'
    styles.push({
      textAlign: isNum ? 'right' : 'left',
      fontFeatureSettings: isNum ? '"tnum"' : 'normal',
    })
  }
  return styles
})
</script>

<template>
  <details class="data-detail" open>
    <summary>📊 数据明细</summary>
    <div class="data-inner">
      <table>
        <colgroup>
          <col v-for="(s, i) in colStyle" :key="i" :style="s" />
        </colgroup>
        <thead>
          <tr>
            <th v-for="h in headers" :key="h">{{ h }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in rows" :key="ri">
            <td v-for="(cell, ci) in row" :key="ci">
              {{ cell }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </details>
</template>

<style lang="scss" scoped>
.data-detail {
  border-top: 1px solid var(--el-border-color-light);
  font-size: 12px;
  max-height: 180px;
  overflow: auto;
  flex-shrink: 0;
}

.data-detail summary {
  cursor: pointer;
  padding: 6px 12px;
  color: #94a3b8;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 1;
}
.data-detail summary:hover {
  color: var(--el-text-color-primary);
}

.data-detail table {
  min-width: 100%;
  table-layout: auto;
  border-collapse: collapse;
  font-size: 12px;
}

.data-detail th {
  position: sticky;
  top: 0;
  text-align: left;
  padding: 4px 8px;
  color: #94a3b8;
  font-weight: 500;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  white-space: nowrap;
}

.data-detail td {
  padding: 3px 8px;
  color: #94a3b8;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  white-space: nowrap;
}
</style>
