<script setup lang="ts">
import type { SluggishItem } from '@/types/inventory'
import { formatDays } from '@/utils/format'

defineProps<{ data: SluggishItem[] }>()

function levelBadge(level: string) {
  return level === 'red' ? '紧急' : level === 'amber' ? '关注' : '跟踪'
}
function levelType(level: string): 'danger' | 'warning' | 'success' {
  return level === 'red' ? 'danger' : level === 'amber' ? 'warning' : 'success'
}
</script>

<template>
  <el-table :data="data" size="small" stripe max-height="420" style="width: 100%">
    <el-table-column type="index" label="#" width="46" />
    <el-table-column prop="code" label="物料编码" min-width="110" show-overflow-tooltip>
      <template #default="{ row }">
        <span style="font-size: 11px; font-family: monospace">{{ row.code }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="name" label="物料名称" min-width="167" show-overflow-tooltip />
    <el-table-column prop="age" label="库龄(天)" min-width="76" sortable>
      <template #default="{ row }">
        <span :style="row.level !== 'green' ? { color: row.level === 'red' ? '#f43f5e' : '#f59e0b', fontWeight: 600 } : {}">{{ formatDays(row.age) }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="amount" label="金额(万)" min-width="76" sortable>
      <template #default="{ row }">¥{{ row.amount }}万</template>
    </el-table-column>
    <el-table-column prop="quantity" label="物资数量" min-width="76" sortable />
    <el-table-column prop="unit" label="单位" min-width="56" />
    <el-table-column prop="project" label="来源项目编码" min-width="130" show-overflow-tooltip>
      <template #default="{ row }">
        <span>{{ row.project || '非项目' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="projectName" label="来源项目名称" min-width="200" show-overflow-tooltip>
      <template #default="{ row }">
        <span>{{ row.projectName || '非项目' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="buyer" label="采购人" min-width="72" />
    <el-table-column prop="level" label="优先级" min-width="72">
      <template #default="{ row }">
        <el-tag :type="levelType(row.level)" size="small" effect="dark">{{ levelBadge(row.level) }}</el-tag>
      </template>
    </el-table-column>
    <!-- 处置建议列暂时隐藏 -->
    <!-- <el-table-column prop="suggest" label="处置建议" width="110">
      <template #default="{ row }">
        <el-tag :type="suggestType(row.suggest)" size="small" effect="plain">{{ row.suggest }}</el-tag>
      </template>
    </el-table-column> -->
  </el-table>
</template>
