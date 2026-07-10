<script setup lang="ts">
defineProps<{
  message: string
}>()

const emit = defineEmits<{
  retry: []
}>()
</script>

<template>
  <el-result
    icon="error"
    title="数据加载失败"
    :sub-title="message"
  >
    <template #extra>
      <el-button type="primary" @click="emit('retry')">
        重新加载
      </el-button>
    </template>
  </el-result>
</template>
