import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ========== State ==========
  const sidebarCollapsed = ref(false)
  const globalError = ref<string | null>(null)

  // ========== Actions ==========
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setGlobalError(message: string | null) {
    globalError.value = message
  }

  return {
    sidebarCollapsed,
    globalError,
    toggleSidebar,
    setGlobalError,
  }
})
