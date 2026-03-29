export function useFolioOps({
  api,
  actionLoading,
  selectedFolio,
  folioChargeForm,
  folioPaymentForm,
  folioReversalForm,
  folioSplitForm,
  folioMergeForm,
  receiptPreview,
  invoicePreview,
  printJob,
  clearMessages,
  messages,
  refreshDashboard,
}) {
  async function postFolioPayment() {
    if (actionLoading.folioPayment) return
    clearMessages()
    actionLoading.folioPayment = true
    try {
      await api(`/api/v1/folios/${selectedFolio.value.id}/payments`, {
        method: 'POST',
        body: JSON.stringify(folioPaymentForm),
      })
      await refreshDashboard()
      messages.success = 'Folio payment posted.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioPayment = false
    }
  }

  async function postFolioCharge() {
    if (actionLoading.folioCharge) return
    clearMessages()
    actionLoading.folioCharge = true
    try {
      await api(`/api/v1/folios/${selectedFolio.value.id}/charges`, {
        method: 'POST',
        body: JSON.stringify(folioChargeForm),
      })
      await refreshDashboard()
      messages.success = 'Manual folio charge posted.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioCharge = false
    }
  }

  async function postFolioReversal() {
    if (actionLoading.folioReversal) return
    clearMessages()
    actionLoading.folioReversal = true
    try {
      await api(`/api/v1/folios/${selectedFolio.value.id}/reversals`, {
        method: 'POST',
        body: JSON.stringify(folioReversalForm),
      })
      await refreshDashboard()
      messages.success = 'Folio reversal posted.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioReversal = false
    }
  }

  async function splitFolioBill() {
    if (actionLoading.folioSplit) return
    clearMessages()
    actionLoading.folioSplit = true
    try {
      const allocations = folioSplitForm.allocations.split(',').map((row) => row.trim()).filter(Boolean)
      await api(`/api/v1/folios/${selectedFolio.value.id}/split`, {
        method: 'POST',
        body: JSON.stringify({ allocations }),
      })
      await refreshDashboard()
      messages.success = 'Folio split created.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioSplit = false
    }
  }

  async function mergeFoliosBill() {
    if (actionLoading.folioMerge) return
    clearMessages()
    actionLoading.folioMerge = true
    try {
      await api('/api/v1/folios/merge', {
        method: 'POST',
        body: JSON.stringify(folioMergeForm),
      })
      await refreshDashboard()
      messages.success = 'Folios merged.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioMerge = false
    }
  }

  async function loadFolioReceipt() {
    if (actionLoading.folioReceipt) return
    clearMessages()
    actionLoading.folioReceipt = true
    try {
      receiptPreview.value = await api(`/api/v1/folios/${selectedFolio.value.id}/receipt`)
      messages.success = 'Folio receipt loaded.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioReceipt = false
    }
  }

  async function loadFolioInvoice() {
    if (actionLoading.folioInvoice) return
    clearMessages()
    actionLoading.folioInvoice = true
    try {
      invoicePreview.value = await api(`/api/v1/folios/${selectedFolio.value.id}/invoice`)
      messages.success = 'Folio invoice loaded.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioInvoice = false
    }
  }

  async function queueFolioPrint() {
    if (actionLoading.folioPrint) return
    clearMessages()
    actionLoading.folioPrint = true
    try {
      printJob.value = await api(`/api/v1/folios/${selectedFolio.value.id}/print`, { method: 'POST' })
      messages.success = 'Print job queued.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioPrint = false
    }
  }

  async function queueFolioInvoicePrint() {
    if (actionLoading.folioPrintInvoice) return
    clearMessages()
    actionLoading.folioPrintInvoice = true
    try {
      printJob.value = await api(`/api/v1/folios/${selectedFolio.value.id}/print-invoice`, { method: 'POST' })
      messages.success = 'Invoice print job queued.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.folioPrintInvoice = false
    }
  }

  return {
    postFolioPayment,
    postFolioCharge,
    postFolioReversal,
    splitFolioBill,
    mergeFoliosBill,
    loadFolioReceipt,
    loadFolioInvoice,
    queueFolioPrint,
    queueFolioInvoicePrint,
  }
}
