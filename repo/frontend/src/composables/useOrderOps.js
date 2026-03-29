function parseSplitAllocations(text) {
  return text
    .split(';')
    .map((row) => row.trim())
    .filter(Boolean)
    .map((row) => {
      const [supplier, warehouse, sla_tier, quantity] = row.split('|').map((part) => (part || '').trim())
      return { supplier, warehouse, sla_tier, quantity: Number(quantity || 0) }
    })
}

export function useOrderOps({
  api,
  actionLoading,
  selectedOrder,
  orderOpsForm,
  clearMessages,
  messages,
  refreshDashboard,
}) {
  async function transitionOrderState() {
    if (actionLoading.orderTransition) return
    clearMessages()
    actionLoading.orderTransition = true
    try {
      await api(`/api/v1/orders/${selectedOrder.value.id}/transition`, {
        method: 'POST',
        body: JSON.stringify({ next_state: orderOpsForm.next_state, reversal_reason: orderOpsForm.reversal_reason || null }),
      })
      await refreshDashboard()
      messages.success = 'Order state updated.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.orderTransition = false
    }
  }

  async function splitOrderDims() {
    if (actionLoading.orderSplit) return
    clearMessages()
    actionLoading.orderSplit = true
    try {
      await api(`/api/v1/orders/${selectedOrder.value.id}/split`, {
        method: 'POST',
        body: JSON.stringify({ allocations: parseSplitAllocations(orderOpsForm.split_allocations) }),
      })
      await refreshDashboard()
      messages.success = 'Order allocations split.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.orderSplit = false
    }
  }

  async function mergeOrderDims() {
    if (actionLoading.orderMerge) return
    clearMessages()
    actionLoading.orderMerge = true
    try {
      await api(`/api/v1/orders/${selectedOrder.value.id}/merge`, {
        method: 'POST',
        body: JSON.stringify({
          supplier: orderOpsForm.merge_supplier,
          warehouse: orderOpsForm.merge_warehouse,
          sla_tier: orderOpsForm.merge_sla_tier,
        }),
      })
      await refreshDashboard()
      messages.success = 'Order allocations merged.'
    } catch (error) {
      messages.error = error.message
    } finally {
      actionLoading.orderMerge = false
    }
  }

  return { transitionOrderState, splitOrderDims, mergeOrderDims }
}
