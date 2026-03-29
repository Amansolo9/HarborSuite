import { computed, ref } from 'vue'

function parseSpecs(specText) {
  return Object.fromEntries(
    String(specText || '')
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const [key, value] = part.split('=')
        return [key?.trim() || '', value?.trim() || '']
      })
      .filter(([k]) => k)
  )
}

function toEpochMs(value) {
  if (!value) {
    return Number.NaN
  }
  if (typeof value !== 'string') {
    return new Date(value).getTime()
  }
  const hasZone = /([zZ]|[+-]\d{2}:\d{2})$/.test(value)
  return new Date(hasZone ? value : `${value}Z`).getTime()
}

export function useOrderQuoteFlow({ api, selectedFolio, refreshDashboard, clearMessages, messages, loading }) {
  const pendingQuote = ref(null)
  const pendingOrderPayload = ref(null)
  const localQuoteConfirmedAtMs = ref(0)

  const effectiveQuoteExpiryMs = computed(() => {
    if (!pendingQuote.value) {
      return 0
    }
    const parsedBackendMs = toEpochMs(pendingQuote.value.expires_at)
    const backendExpiresMs = Number.isFinite(parsedBackendMs) ? parsedBackendMs : Number.POSITIVE_INFINITY
    const localTenMinuteMs = localQuoteConfirmedAtMs.value > 0 ? localQuoteConfirmedAtMs.value + 10 * 60 * 1000 : Number.POSITIVE_INFINITY
    return Math.min(backendExpiresMs, localTenMinuteMs)
  })

  const quoteExpired = computed(() => {
    if (!pendingQuote.value) {
      return false
    }
    return effectiveQuoteExpiryMs.value <= Date.now()
  })

  const quoteExpiryDisplay = computed(() => {
    if (!pendingQuote.value || !effectiveQuoteExpiryMs.value || !Number.isFinite(effectiveQuoteExpiryMs.value)) {
      return pendingQuote.value?.expires_at || ''
    }
    return new Date(effectiveQuoteExpiryMs.value).toISOString()
  })

  function clearPendingQuote() {
    pendingQuote.value = null
    pendingOrderPayload.value = null
    localQuoteConfirmedAtMs.value = 0
  }

  async function createOrder(orderForm) {
    clearMessages()
    loading.order = true
    try {
      const hasCartPayload = Array.isArray(orderForm.items)
      const sharedPayload = {
        folio_id: selectedFolio.value.id,
        items: hasCartPayload
          ? orderForm.items
          : [
              {
                sku: orderForm.sku || null,
                name: orderForm.name,
                quantity: orderForm.quantity,
                unit_price: orderForm.unit_price,
                size: orderForm.size,
                specs: parseSpecs(orderForm.specs),
                delivery_slot_label: orderForm.delivery_slot_label || '',
              },
            ],
        payment_method: orderForm.payment_method,
        packaging_fee: orderForm.packaging_fee,
        service_fee: orderForm.service_fee,
        tax_rate: '0.10',
        order_note: orderForm.order_note || null,
        delivery_window_start: new Date(orderForm.delivery_start).toISOString(),
        delivery_window_end: new Date(orderForm.delivery_end).toISOString(),
      }
      const quote = await api('/api/v1/orders/confirm-quote', {
        method: 'POST',
        body: JSON.stringify(sharedPayload),
      })
      pendingQuote.value = quote
      pendingOrderPayload.value = sharedPayload
      localQuoteConfirmedAtMs.value = Date.now()
      messages.success = 'Quote confirmed. Review and submit before expiration.'
    } catch (error) {
      messages.error = error.message
    } finally {
      loading.order = false
    }
  }

  async function submitConfirmedOrder() {
    clearMessages()
    if (quoteExpired.value) {
      clearPendingQuote()
      messages.error = 'Quote expired. Reconfirm pricing before submit.'
      return
    }
    if (!pendingQuote.value || !pendingOrderPayload.value) {
      messages.error = 'No confirmed quote available. Confirm pricing first.'
      return
    }
    try {
      await api('/api/v1/orders', {
        method: 'POST',
        body: JSON.stringify({
          ...pendingOrderPayload.value,
          price_confirmed_at: new Date().toISOString(),
          reconfirm_token: pendingQuote.value.reconfirm_token,
        }),
      })
      clearPendingQuote()
      await refreshDashboard()
      messages.success = 'Order created and posted to the selected folio.'
    } catch (error) {
      if (String(error.message).toLowerCase().includes('reconfirm') || String(error.message).toLowerCase().includes('changed')) {
        clearPendingQuote()
        messages.error = 'Pricing or tax changed. Reconfirm quote and submit again.'
        return
      }
      messages.error = error.message
    }
  }

  function resetOrderQuoteState() {
    clearPendingQuote()
  }

  return {
    pendingQuote,
    quoteExpiryDisplay,
    quoteExpired,
    createOrder,
    clearPendingQuote,
    submitConfirmedOrder,
    resetOrderQuoteState,
  }
}
