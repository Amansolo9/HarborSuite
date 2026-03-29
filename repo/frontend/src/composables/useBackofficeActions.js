import { reactive, ref } from 'vue'

export function useBackofficeActions({ api, clearMessages, messages, ratings, lineageRows }) {
  const nightAuditResult = ref(null)
  const dayCloseResult = ref(null)
  const creditProfile = ref(null)
  const ratingForm = reactive({ to_username: 'service@seabreeze.local', score: 5, comment: 'Great service', order_id: '' })
  const datasetForm = reactive({ dataset_name: 'ops_snapshot', version: 'v1', dataset_schema_json: '{"folio_id":"string","amount":"decimal"}' })
  const lineageForm = reactive({ metric_name: 'ops_efficiency', dataset_version_id: '', source_tables_csv: 'orders,folios', source_query_ref: 'query://ops/efficiency/v1' })
  const closeForm = reactive({ business_date: '', all_organizations: false })
  const nightAuditForm = reactive({ all_organizations: false })
  const creditForm = reactive({ username: 'guest@seabreeze.local', rating: 5, penalty: '0.00', violation: false, note: '' })
  const creditLookupUsername = ref('guest@seabreeze.local')
  const backofficeLoading = reactive({
    submitRating: false,
    createDataset: false,
    createLineage: false,
    runNightAudit: false,
    runDayClose: false,
    calculateCredit: false,
    loadCreditProfile: false,
  })

  async function submitRating() {
    if (backofficeLoading.submitRating) {
      return
    }
    backofficeLoading.submitRating = true
    clearMessages()
    try {
      await api('/api/v1/ratings', {
        method: 'POST',
        body: JSON.stringify(ratingForm),
      })
      ratings.value = await api('/api/v1/ratings/me')
      messages.success = 'Rating submitted.'
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.submitRating = false
    }
  }

  async function createDataset() {
    if (backofficeLoading.createDataset) {
      return
    }
    backofficeLoading.createDataset = true
    clearMessages()
    try {
      const dataset = await api('/api/v1/governance/datasets', {
        method: 'POST',
        body: JSON.stringify({
          dataset_name: datasetForm.dataset_name,
          version: datasetForm.version,
          dataset_schema: JSON.parse(datasetForm.dataset_schema_json),
        }),
      })
      lineageForm.dataset_version_id = dataset.id
      lineageRows.value = await api('/api/v1/governance/lineage')
      messages.success = 'Dataset version registered.'
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.createDataset = false
    }
  }

  async function createLineage() {
    if (backofficeLoading.createLineage) {
      return
    }
    backofficeLoading.createLineage = true
    clearMessages()
    try {
      await api('/api/v1/governance/lineage', {
        method: 'POST',
        body: JSON.stringify({
          metric_name: lineageForm.metric_name,
          dataset_version_id: lineageForm.dataset_version_id,
          source_tables: lineageForm.source_tables_csv.split(',').map((v) => v.trim()).filter(Boolean),
          source_query_ref: lineageForm.source_query_ref,
        }),
      })
      lineageRows.value = await api('/api/v1/governance/lineage')
      messages.success = 'Lineage link registered.'
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.createLineage = false
    }
  }

  async function runNightAudit() {
    if (backofficeLoading.runNightAudit) {
      return
    }
    backofficeLoading.runNightAudit = true
    clearMessages()
    try {
      nightAuditResult.value = await api('/api/v1/night-audit/run', {
        method: 'POST',
        body: JSON.stringify(nightAuditForm),
      })
      messages.success = 'Night audit run completed.'
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.runNightAudit = false
    }
  }

  async function runDayCloseAction() {
    if (backofficeLoading.runDayClose) {
      return
    }
    backofficeLoading.runDayClose = true
    clearMessages()
    try {
      dayCloseResult.value = await api('/api/v1/day-close/run', {
        method: 'POST',
        body: JSON.stringify(closeForm),
      })
      messages.success = 'Day-close run completed.'
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.runDayClose = false
    }
  }

  async function loadCreditProfile(explicitUsername = null, opts = {}) {
    if (backofficeLoading.loadCreditProfile && !opts.ignoreInFlight) {
      return
    }
    backofficeLoading.loadCreditProfile = true
    if (!opts.preserveMessages) {
      clearMessages()
    }
    const username = explicitUsername || creditLookupUsername.value
    try {
      creditProfile.value = await api(`/api/v1/credit-score/${encodeURIComponent(username)}`)
      if (!opts.preserveMessages) {
        messages.success = 'Credit profile loaded.'
      }
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.loadCreditProfile = false
    }
  }

  async function calculateCreditScore() {
    if (backofficeLoading.calculateCredit) {
      return
    }
    backofficeLoading.calculateCredit = true
    clearMessages()
    try {
      await api('/api/v1/credit-score/calculate', {
        method: 'POST',
        body: JSON.stringify({
          username: creditForm.username,
          rating: creditForm.rating,
          penalties: [creditForm.penalty],
          violation: creditForm.violation,
          note: creditForm.note,
        }),
      })
      await loadCreditProfile(creditForm.username, { preserveMessages: true, ignoreInFlight: true })
      messages.success = 'Credit score updated.'
    } catch (error) {
      messages.error = error.message
    } finally {
      backofficeLoading.calculateCredit = false
    }
  }

  function resetBackofficeState() {
    nightAuditResult.value = null
    dayCloseResult.value = null
    creditProfile.value = null
    for (const key of Object.keys(backofficeLoading)) {
      backofficeLoading[key] = false
    }
  }

  return {
    ratingForm,
    datasetForm,
    lineageForm,
    closeForm,
    nightAuditForm,
    creditForm,
    creditLookupUsername,
    nightAuditResult,
    dayCloseResult,
    creditProfile,
    backofficeLoading,
    submitRating,
    createDataset,
    createLineage,
    runNightAudit,
    runDayCloseAction,
    calculateCreditScore,
    loadCreditProfile,
    resetBackofficeState,
  }
}
