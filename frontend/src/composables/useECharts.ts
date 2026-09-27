import { onBeforeUnmount, onMounted } from 'vue'
import { echarts } from '@/utils/echarts'

/**
 * ECharts 实例生命周期管理 composable
 *
 * 用法:
 *   const chart = useECharts()
 *   chart.init(ref.value)
 *   chart.setOption({ ... })
 *   // 组件卸载时自动 dispose, 自动监听 window resize
 */
export function useECharts() {
  let instance: ReturnType<typeof echarts.init> | null = null
  let observer: ResizeObserver | null = null
  let rafId: number | null = null

  function init(dom: HTMLElement) {
    const existing = echarts.getInstanceByDom(dom)
    if (existing) existing.dispose()
    instance = echarts.init(dom)

    // 监听容器尺寸变化自动 resize。flex 布局下 DOM 尺寸是异步（nextTick 后）才更新的，
    // 仅靠 window resize 会读到旧尺寸，导致 canvas 高度滞后、溢出卡片出现滚动条。
    // 用 rAF 合并同一帧内的多次尺寸抖动，避免 flex 布局稳定前高频 resize 造成闪烁。
    observer?.disconnect()
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(() => {
        if (rafId != null) return
        rafId = requestAnimationFrame(() => {
          rafId = null
          instance?.resize()
        })
      })
      observer.observe(dom)
    }
  }

  function setOption(option: Record<string, unknown>) {
    instance?.setOption(option, true)
  }

  function onResize() {
    instance?.resize()
  }

  function dispose() {
    observer?.disconnect()
    observer = null
    if (rafId != null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    instance?.dispose()
    instance = null
  }

  onMounted(() => window.addEventListener('resize', onResize))
  onBeforeUnmount(() => {
    window.removeEventListener('resize', onResize)
    dispose()
  })

  return { init, setOption, resize: onResize, dispose, get instance() { return instance } }
}
