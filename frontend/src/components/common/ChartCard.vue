<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<template>
  <el-card class="chart-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <span>{{ title }}</span>
        <slot name="actions" />
      </div>
    </template>
    <slot />
  </el-card>
</template>

<style lang="scss" scoped>
.chart-card {
  margin-bottom: 8px;
}
</style>
