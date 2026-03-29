import { computed, reactive, ref } from 'vue'

export function useComplaintFlow({ api, selectedFolio, orders, refreshDashboard, clearMessages, messages, loading }) {
  const complaintPacket = ref(null)
  const lastComplaintId = ref('')
  const complaintForm = reactive({
    subject: 'Late delivery',
    detail: 'Please investigate the room-service delay.',
    service_rating: 2,
    violation_flag: false,
  })

  const complaintEligibility = computed(() => {
    if (!selectedFolio.value) {
      return { eligible: false, reason: 'Select a folio first.' }
    }
    const related = orders.value
      .filter((order) => order.folio_id === selectedFolio.value.id)
      .map((order) => new Date(order.service_end_at || order.delivery_window_end))
      .filter((date) => !Number.isNaN(date.getTime()))
      .sort((a, b) => b.getTime() - a.getTime())
    if (!related.length) {
      return { eligible: false, reason: 'No completed service timeline found for this folio yet.' }
    }
    const latest = related[0]
    const days = (Date.now() - latest.getTime()) / (1000 * 60 * 60 * 24)
    if (days > 7) {
      return { eligible: false, reason: `Complaint window closed (last service ${latest.toLocaleString()}).` }
    }
    return { eligible: true, reason: `Eligible through ${new Date(latest.getTime() + 7 * 24 * 60 * 60 * 1000).toLocaleString()}` }
  })

  async function createComplaint() {
    clearMessages()
    if (!complaintEligibility.value.eligible) {
      messages.error = complaintEligibility.value.reason
      return
    }
    loading.complaint = true
    try {
      const response = await api('/api/v1/complaints', {
        method: 'POST',
        body: JSON.stringify({
          folio_id: selectedFolio.value.id,
          subject: complaintForm.subject,
          detail: complaintForm.detail,
          service_rating: complaintForm.service_rating,
          violation_flag: complaintForm.violation_flag,
        }),
      })
      lastComplaintId.value = response.id
      await refreshDashboard()
      messages.success = 'Complaint filed and added to the audit trail.'
    } catch (error) {
      messages.error = error.message
    } finally {
      loading.complaint = false
    }
  }

  async function exportComplaintPacket() {
    clearMessages()
    if (!lastComplaintId.value) {
      messages.error = 'No complaint selected for packet export.'
      return
    }
    try {
      complaintPacket.value = await api(`/api/v1/complaints/${lastComplaintId.value}/packet`)
      messages.success = 'Complaint packet generated.'
    } catch (error) {
      messages.error = error.message
    }
  }

  function resetComplaintState() {
    complaintPacket.value = null
    lastComplaintId.value = ''
  }

  return {
    complaintPacket,
    lastComplaintId,
    complaintForm,
    complaintEligibility,
    createComplaint,
    exportComplaintPacket,
    resetComplaintState,
  }
}
