import { ref, onMounted, onBeforeUnmount } from 'vue'

/**
 * 响应式时钟 composable
 *
 * 返回 currentTime ref，每秒钟自动更新一次，
 * 组件卸载时自动清除定时器。
 */
export function useClock() {
  const currentTime = ref('')
  let timer: ReturnType<typeof setInterval> | null = null

  function update() {
    const now = new Date()
    currentTime.value = now.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  onMounted(() => {
    update()
    timer = setInterval(update, 1000)
  })

  onBeforeUnmount(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  })

  return { currentTime }
}
