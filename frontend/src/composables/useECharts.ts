import { onBeforeUnmount } from 'vue'
import { echarts } from '@/utils/echarts'

/**
 * ECharts 实例生命周期管理 composable
 *
 * 用法:
 *   const chart = useECharts()
 *   chart.init(ref.value)
 *   chart.setOption({ ... })
 *   // 组件卸载时自动 dispose
 */
export function useECharts() {
  let instance: ReturnType<typeof echarts.init> | null = null

  function init(dom: HTMLElement) {
    // 先销毁同一 DOM 上的已有实例，防止路由切换时重复 init 冲突
    const existing = echarts.getInstanceByDom(dom)
    if (existing) {
      existing.dispose()
    }
    instance = echarts.init(dom)
  }

  function setOption(option: Record<string, unknown>) {
    instance?.setOption(option, true)
  }

  function resize() {
    instance?.resize()
  }

  function dispose() {
    instance?.dispose()
    instance = null
  }

  onBeforeUnmount(() => {
    dispose()
  })

  return { init, setOption, resize, dispose, get instance() { return instance } }
}
