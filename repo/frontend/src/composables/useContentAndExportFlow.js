import { reactive, ref } from 'vue'

export function useContentAndExportFlow({ api, refreshDashboard, clearMessages, messages, loading }) {
  const latestExport = ref(null)
  const releaseForm = reactive({
    title: 'Lobby piano update',
    body: 'Tonight live set moves to the west lounge at 20:00.',
    tags_csv: 'nightlife',
    roles_csv: 'guest',
    content_type: 'announcement',
    organizations: 'all',
  })
  const exportForm = reactive({ export_type: 'daily-audit', scope: 'property-close' })

  async function createRelease() {
    clearMessages()
    loading.release = true
    try {
      await api('/api/v1/content/releases', {
        method: 'POST',
        body: JSON.stringify({
          title: releaseForm.title,
          body: releaseForm.body,
          content_type: releaseForm.content_type,
          target_roles: releaseForm.roles_csv.split(',').map((part) => part.trim()).filter(Boolean),
          target_tags: releaseForm.tags_csv.split(',').map((part) => part.trim()).filter(Boolean),
          target_organizations: releaseForm.organizations.split(',').map((part) => part.trim()).filter(Boolean),
        }),
      })
      await refreshDashboard()
      messages.success = 'Content release created and queued for approval.'
    } catch (error) {
      messages.error = error.message
    } finally {
      loading.release = false
    }
  }

  async function approveRelease(releaseId) {
    clearMessages()
    try {
      await api(`/api/v1/content/releases/${releaseId}/approve`, { method: 'POST' })
      await refreshDashboard()
      messages.success = 'Release approved.'
    } catch (error) {
      messages.error = error.message
    }
  }

  async function rollbackRelease(releaseId) {
    clearMessages()
    try {
      await api(`/api/v1/content/releases/${releaseId}/rollback`, { method: 'POST' })
      await refreshDashboard()
      messages.success = 'Release rollback created.'
    } catch (error) {
      messages.error = error.message
    }
  }

  async function createExportBundle() {
    clearMessages()
    loading.exportBundle = true
    try {
      latestExport.value = await api('/api/v1/exports', {
        method: 'POST',
        body: JSON.stringify(exportForm),
      })
      await refreshDashboard()
      messages.success = 'Offline export bundle created.'
    } catch (error) {
      messages.error = error.message
    } finally {
      loading.exportBundle = false
    }
  }

  function resetContentAndExportState() {
    latestExport.value = null
  }

  return {
    releaseForm,
    exportForm,
    latestExport,
    createRelease,
    approveRelease,
    rollbackRelease,
    createExportBundle,
    resetContentAndExportState,
  }
}
