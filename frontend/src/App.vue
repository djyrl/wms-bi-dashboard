<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Layout from '@/layout/Layout.vue'
import ScreenAdapter from '@/components/common/ScreenAdapter.vue'

const route = useRoute()
const isFullscreen = computed(() => route.meta?.fullscreen === true)
</script>

<template>
  <Layout v-if="!isFullscreen">
    <router-view />
  </Layout>
  <div v-else class="fullscreen-viewport"><ScreenAdapter><router-view /></ScreenAdapter></div>
</template>

<style>
html, body, #app {
  height: 100%;
}
.fullscreen-viewport {
  height: 100%;
  overflow: hidden;
}
</style>
