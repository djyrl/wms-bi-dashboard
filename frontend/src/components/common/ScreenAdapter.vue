<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(
  defineProps<{
    designWidth?: number
    designHeight?: number
  }>(),
  {
    designWidth: 1920,
    designHeight: 1080,
  },
)

const scale = ref(1)
const canvasHeight = ref(props.designHeight)

function updateScale() {
  // 只按宽度等比缩放，画布高度动态匹配视口，保证任何宽高比下都铺满、无黑边
  scale.value = window.innerWidth / props.designWidth
  canvasHeight.value = window.innerHeight / scale.value
}

onMounted(() => {
  updateScale()
  window.addEventListener('resize', updateScale)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateScale)
})
</script>

<template>
  <div class="screen-adapter">
    <div
      class="screen-canvas"
      :style="{
        width: props.designWidth + 'px',
        height: canvasHeight + 'px',
        transform: `scale(${scale})`,
      }"
    >
      <slot />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.screen-adapter {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.screen-canvas {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: top left;
}
</style>
