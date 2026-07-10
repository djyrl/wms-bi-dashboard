import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getKpiChecklist } from '@/api/modules/kpiChecklist'
import type { KpiChecklistRes, KpiItem } from '@/api/modules/kpiChecklist'

export const useKpiChecklistStore = defineStore('kpiChecklist', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  const summary = ref<KpiChecklistRes['summary'] | null>(null)
  const coreKpis = ref<Record<string, KpiItem>>({})
  const constraintKpis = ref<Record<string, KpiItem>>({})
  const structureKpis = ref<KpiChecklistRes['structure_kpis'] | null>(null)
  const topKpis = ref<KpiChecklistRes['top_kpis'] | null>(null)

  /** 获取所有状态为 warning 或 alert 的 KPI */
  function getAlertKpis(): KpiItem[] {
    const all = [
      ...Object.values(coreKpis.value),
      ...Object.values(constraintKpis.value),
    ]
    return all.filter((k) => k.status === 'warning' || k.status === 'alert')
  }

  async function loadAllData() {
    loading.value = true
    error.value = null
    try {
      const data = await getKpiChecklist()
      summary.value = data.summary
      coreKpis.value = data.core_kpis
      constraintKpis.value = data.constraint_kpis
      structureKpis.value = data.structure_kpis
      topKpis.value = data.top_kpis
    } catch (e: any) {
      console.error('KPI考核清单数据加载失败:', e)
      error.value = e?.message || '数据加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    summary,
    coreKpis,
    constraintKpis,
    structureKpis,
    topKpis,
    getAlertKpis,
    loadAllData,
  }
})
