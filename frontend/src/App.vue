<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Layout from '@/layout/Layout.vue'

const route = useRoute()
const isFullscreen = computed(() => route.meta?.fullscreen === true)
</script>

<template>
  <Layout v-if="!isFullscreen">
    <router-view />
  </Layout>
  <router-view v-else />
</template>
