import { ref } from 'vue'

export function useDashboardData({ api, session, loading, messages, clearMessages, onAuthFailure, ratingForm }) {
  const folios = ref([])
  const orders = ref([])
  const ratings = ref([])
  const releases = ref([])
  const auditLogs = ref([])
  const lineageRows = ref([])
  const serviceDurationMetrics = ref([])
  const gmDashboardMetrics = ref(null)
  const selectedFolio = ref(null)
  const selectedOrder = ref(null)

  async function loadServiceDurations(showMessage = true) {
    loading.serviceDuration = true
    try {
      const response = await api('/api/v1/analytics/service-durations')
      serviceDurationMetrics.value = response.metrics || []
      if (showMessage) {
        messages.success = 'Service duration metrics refreshed.'
      }
    } catch (error) {
      messages.error = error.message
    } finally {
      loading.serviceDuration = false
    }
  }

  async function loadGmDashboard(showMessage = true) {
    loading.gmDashboard = true
    try {
      gmDashboardMetrics.value = await api('/api/v1/analytics/gm-dashboard')
      if (showMessage) {
        messages.success = 'GM dashboard metrics refreshed.'
      }
    } catch (error) {
      messages.error = error.message
    } finally {
      loading.gmDashboard = false
    }
  }

  async function refreshDashboard() {
    loading.dashboard = true
    try {
      clearMessages()
      const [user, overviewData, folioData, orderData, releaseData] = await Promise.all([
        api('/api/v1/auth/me'),
        api('/api/v1/operations/overview'),
        api('/api/v1/folios'),
        api('/api/v1/orders'),
        api('/api/v1/content/releases'),
      ])

      session.user = user
      session.overview = overviewData
      folios.value = folioData
      orders.value = orderData
      releases.value = releaseData
      selectedFolio.value = folioData[0] || null
      selectedOrder.value = orderData[0] || null
      ratingForm.order_id = orderData[0]?.id || ''

      if (user.role === 'general_manager') {
        auditLogs.value = await api('/api/v1/audit/logs')
      } else {
        auditLogs.value = []
      }

      if (['guest', 'service_staff'].includes(user.role)) {
        ratings.value = await api('/api/v1/ratings/me')
      } else {
        ratings.value = []
      }

      if (['finance', 'general_manager'].includes(user.role)) {
        lineageRows.value = await api('/api/v1/governance/lineage')
      } else {
        lineageRows.value = []
      }

      if (['service_staff', 'finance', 'general_manager'].includes(user.role)) {
        await loadServiceDurations(false)
      } else {
        serviceDurationMetrics.value = []
      }

      if (user.role === 'general_manager') {
        await loadGmDashboard(false)
      } else {
        gmDashboardMetrics.value = null
      }
    } catch (error) {
      onAuthFailure(error)
    } finally {
      loading.dashboard = false
    }
  }

  function resetDashboardData() {
    folios.value = []
    orders.value = []
    ratings.value = []
    releases.value = []
    auditLogs.value = []
    lineageRows.value = []
    serviceDurationMetrics.value = []
    gmDashboardMetrics.value = null
    selectedFolio.value = null
    selectedOrder.value = null
  }

  return {
    folios,
    orders,
    ratings,
    releases,
    auditLogs,
    lineageRows,
    serviceDurationMetrics,
    gmDashboardMetrics,
    selectedFolio,
    selectedOrder,
    refreshDashboard,
    loadServiceDurations,
    loadGmDashboard,
    resetDashboardData,
  }
}
