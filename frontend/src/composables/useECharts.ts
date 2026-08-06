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

  function init(dom: HTMLElement) {
    const existing = echarts.getInstanceByDom(dom)
    if (existing) existing.dispose()
    instance = echarts.init(dom)
  }

  function setOption(option: Record<string, unknown>) {
    instance?.setOption(option, true)
  }

  function onResize() {
    instance?.resize()
  }

  function dispose() {
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
