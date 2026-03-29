import { reactive, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { useOrderQuoteFlow } from './useOrderQuoteFlow'

describe('useOrderQuoteFlow', () => {
  it('enforces local 10-minute quote TTL even if backend expiry is later', async () => {
    const selectedFolio = ref({ id: 'f1' })
    const messages = reactive({ success: '', error: '' })
    const loading = reactive({ order: false })
    const clearMessages = () => {
      messages.success = ''
      messages.error = ''
    }

    const api = vi.fn(async (path) => {
      if (path === '/api/v1/orders/confirm-quote') {
        return {
          reconfirm_token: 'rq1',
          quote_hash: 'hash-1',
          expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        }
      }
      return { id: 'o1' }
    })

    const flow = useOrderQuoteFlow({
      api,
      selectedFolio,
      refreshDashboard: async () => {},
      clearMessages,
      messages,
      loading,
    })

    const nowSpy = vi.spyOn(Date, 'now')
    nowSpy.mockReturnValue(1_000_000)

    await flow.createOrder({
      items: [{ name: 'Soup', quantity: 1, unit_price: '12.00', size: 'regular', specs: { salt: 'low' }, delivery_slot_label: '' }],
      payment_method: 'cash',
      packaging_fee: '0.00',
      service_fee: '0.00',
      order_note: '',
      delivery_start: '2026-03-29T18:00',
      delivery_end: '2026-03-29T18:30',
    })

    nowSpy.mockReturnValue(1_000_000 + 11 * 60 * 1000)
    expect(flow.quoteExpired.value).toBe(true)
    nowSpy.mockRestore()
  })
})
