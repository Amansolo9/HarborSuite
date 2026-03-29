import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'

import App from './App.vue'
import CreditPanel from './components/CreditPanel.vue'
import FinanceClosePanel from './components/FinanceClosePanel.vue'
import FolioOperationsPanel from './components/FolioOperationsPanel.vue'
import GovernanceOpsPanel from './components/GovernanceOpsPanel.vue'
import LoginPanel from './components/LoginPanel.vue'
import OrderComposer from './components/OrderComposer.vue'

function response(ok, payload, status = ok ? 200 : 400) {
  return {
    ok,
    status,
    json: async () => payload,
  }
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: App }],
  })
}

describe('App integration workflows', () => {
  it('handles guest quote reconfirm then submit flow', async () => {
    sessionStorage.clear()
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') return response(true, { access_token: 'tok', full_name: 'Maya Chen' })
      if (url === '/api/v1/auth/me') return response(true, { role: 'guest', full_name: 'Maya Chen', organization_name: 'Seabreeze', user_id: 'u1' })
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 1, pending_content: 1, open_complaints: 0, unread_releases: 1, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') return response(true, [{ id: 'o1', state: 'created', payment_method: 'cash', total_amount: '8.50', tax_reconfirm_by: new Date().toISOString() }])
      if (url === '/api/v1/content/releases') return response(true, [])
      if (url === '/api/v1/ratings/me') return response(true, [])
      if (url === '/api/v1/orders/confirm-quote' && method === 'POST') {
        return response(true, { reconfirm_token: 'rq1', quote_hash: 'hash-1', expires_at: new Date(Date.now() + 600000).toISOString() })
      }
      if (url === '/api/v1/orders' && method === 'POST') return response(true, { id: 'o2' })
      return response(false, { detail: `Unhandled ${method} ${url}` }, 400)
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'guest@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()

    wrapper.findComponent(OrderComposer).vm.$emit('submit', {
      items: [
        {
          sku: 'food_club_sandwich',
          name: 'Club sandwich',
          quantity: 1,
          unit_price: '14.00',
          size: 'regular',
          specs: { sauce: 'light' },
          delivery_slot_label: 'Lunch',
        },
        {
          sku: 'late_checkout_2pm',
          name: 'Late checkout extension',
          quantity: 1,
          unit_price: '45.00',
          size: '2pm',
          specs: { floor: 'any' },
          delivery_slot_label: 'Departure day',
        },
      ],
      payment_method: 'direct_bill',
      packaging_fee: '2.50',
      service_fee: '10.62',
      order_note: 'No onion',
      delivery_start: new Date(Date.now() + 60000).toISOString().slice(0, 16),
      delivery_end: new Date(Date.now() + 1800000).toISOString().slice(0, 16),
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Confirm quoted totals before submit')

    const quoteCall = fetchMock.mock.calls.find((call) => call[0] === '/api/v1/orders/confirm-quote')
    expect(quoteCall).toBeTruthy()
    expect(JSON.parse(quoteCall[1].body).items).toHaveLength(2)

    const submitBtn = wrapper.findAll('button').find((btn) => btn.text().includes('Submit confirmed order'))
    await submitBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Order created and posted to the selected folio.')
  })

  it('shows error banner when desk folio reversal fails', async () => {
    sessionStorage.clear()
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') return response(true, { access_token: 'tok', full_name: 'Iris Bell' })
      if (url === '/api/v1/auth/me') return response(true, { role: 'front_desk', full_name: 'Iris Bell', organization_name: 'Seabreeze', user_id: 'u2' })
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 0, pending_content: 0, open_complaints: 0, unread_releases: 0, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') return response(true, [])
      if (url === '/api/v1/content/releases') return response(true, [])
      if (url.includes('/api/v1/folios/f1/reversals') && method === 'POST') return response(false, { detail: 'Desk reversal denied for test' }, 409)
      return response(true, [])
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'desk@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()

    wrapper.findComponent(FolioOperationsPanel).vm.$emit('post-reversal')
    await flushPromises()

    expect(wrapper.text()).toContain('Desk reversal denied for test')
  })

  it('shows role-gated panels by user role', async () => {
    sessionStorage.clear()
    let currentUsername = ''
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') {
        const body = JSON.parse(options.body || '{}')
        currentUsername = body.username
        if (body.username === 'guest@seabreeze.local') {
          return response(true, { access_token: 'tok-guest', full_name: 'Maya Chen' })
        }
        if (body.username === 'finance@seabreeze.local') {
          return response(true, { access_token: 'tok-fin', full_name: 'Noah Silva' })
        }
      }
      if (url === '/api/v1/auth/me') {
        if (currentUsername === 'finance@seabreeze.local') {
          return response(true, { role: 'finance', full_name: 'Noah Silva', organization_name: 'Seabreeze', user_id: 'u-fin' })
        }
        return response(true, { role: 'guest', full_name: 'Maya Chen', organization_name: 'Seabreeze', user_id: 'u-guest' })
      }
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 0, pending_content: 0, open_complaints: 0, unread_releases: 0, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') return response(true, [])
      if (url === '/api/v1/content/releases') return response(true, [])
      if (url === '/api/v1/governance/lineage') return response(true, [])
      return response(true, [])
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'guest@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()
    expect(wrapper.text()).not.toContain('Folio operations')

    const signOutButton = wrapper.findAll('button').find((btn) => btn.text().includes('Sign out'))
    await signOutButton.trigger('click')
    await flushPromises()

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'finance@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()
    expect(wrapper.text()).toContain('Folio operations')
  })

  it('supports gm content approval and rollback actions', async () => {
    sessionStorage.clear()
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') return response(true, { access_token: 'tok-gm', full_name: 'Priya Rao' })
      if (url === '/api/v1/auth/me') return response(true, { role: 'general_manager', full_name: 'Priya Rao', organization_name: 'Seabreeze', user_id: 'u-gm' })
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 0, pending_content: 1, open_complaints: 0, unread_releases: 1, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') return response(true, [])
      if (url === '/api/v1/governance/lineage') return response(true, [])
      if (url === '/api/v1/analytics/gm-dashboard') {
        return response(true, { scale_index: 1, churn_rate: 2.5, participation_rate: 8.1, order_volume: 2, fund_income_expense: '120.50', budget_execution: 64.2, approval_efficiency: 95.0 })
      }
      if (url === '/api/v1/audit/logs') return response(true, [])
      if (url === '/api/v1/content/releases') {
        return response(true, [
          { id: 'r1', title: 'Pool update', content_type: 'announcement', status: 'pending_approval', target_roles: ['guest'], target_tags: ['all'], target_organizations: ['all'], readership_count: 0 },
        ])
      }
      if (url === '/api/v1/content/releases/r1/approve' && method === 'POST') return response(true, { status: 'approved' })
      if (url === '/api/v1/content/releases/r1/rollback' && method === 'POST') return response(true, { status: 'rolled_back' })
      return response(true, [])
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'gm@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()

    const approveBtn = wrapper.findAll('button').find((btn) => btn.text().includes('Approve'))
    await approveBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Release approved.')

    const rollbackBtn = wrapper.findAll('button').find((btn) => btn.text().includes('Rollback'))
    await rollbackBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Release rollback created.')
  })

  it('blocks submit when quote already expired in UI', async () => {
    sessionStorage.clear()
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') return response(true, { access_token: 'tok', full_name: 'Maya Chen' })
      if (url === '/api/v1/auth/me') return response(true, { role: 'guest', full_name: 'Maya Chen', organization_name: 'Seabreeze', user_id: 'u1' })
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 1, pending_content: 1, open_complaints: 0, unread_releases: 1, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') return response(true, [{ id: 'o1', state: 'created', payment_method: 'cash', total_amount: '8.50', tax_reconfirm_by: new Date().toISOString() }])
      if (url === '/api/v1/content/releases') return response(true, [])
      if (url === '/api/v1/ratings/me') return response(true, [])
      if (url === '/api/v1/orders/confirm-quote' && method === 'POST') {
        return response(true, { reconfirm_token: 'rq1', quote_hash: 'hash-1', expires_at: new Date(Date.now() - 1000).toISOString() })
      }
      if (url === '/api/v1/orders' && method === 'POST') return response(true, { id: 'o2' })
      return response(false, { detail: `Unhandled ${method} ${url}` }, 400)
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'guest@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()

    wrapper.findComponent(OrderComposer).vm.$emit('submit', {
      sku: 'food_club_sandwich',
      name: 'Club sandwich',
      quantity: 1,
      unit_price: '14.00',
      size: 'regular',
      specs: 'sauce=light',
      delivery_slot_label: 'Lunch',
      payment_method: 'direct_bill',
      packaging_fee: '2.50',
      service_fee: '0.00',
      order_note: 'No onion',
      delivery_start: new Date(Date.now() + 60000).toISOString().slice(0, 16),
      delivery_end: new Date(Date.now() + 1800000).toISOString().slice(0, 16),
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Quote expired')
    expect(fetchMock.mock.calls.filter((call) => call[0] === '/api/v1/orders' && ((call[1]?.method || 'GET').toUpperCase() === 'POST')).length).toBe(0)
  })

  it('prevents complaint submission outside seven-day window', async () => {
    sessionStorage.clear()
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') return response(true, { access_token: 'tok', full_name: 'Maya Chen' })
      if (url === '/api/v1/auth/me') return response(true, { role: 'guest', full_name: 'Maya Chen', organization_name: 'Seabreeze', user_id: 'u1' })
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 1, pending_content: 0, open_complaints: 0, unread_releases: 0, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') {
        return response(true, [{ id: 'o1', folio_id: 'f1', state: 'delivered', payment_method: 'cash', total_amount: '8.50', delivery_window_end: new Date(Date.now() - 9 * 86400000).toISOString(), service_end_at: new Date(Date.now() - 9 * 86400000).toISOString(), tax_reconfirm_by: new Date().toISOString() }])
      }
      if (url === '/api/v1/content/releases') return response(true, [])
      if (url === '/api/v1/ratings/me') return response(true, [])
      if (url === '/api/v1/complaints' && method === 'POST') return response(true, { id: 'c1' })
      return response(true, [])
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'guest@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()
    expect(wrapper.text()).toContain('Complaint window closed')

    const complaintPostCalls = fetchMock.mock.calls.filter((call) => call[0] === '/api/v1/complaints' && ((call[1]?.method || 'GET').toUpperCase() === 'POST'))
    expect(complaintPostCalls.length).toBe(0)
  })

  it('executes finance and governance operational actions', async () => {
    sessionStorage.clear()
    const fetchMock = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()
      if (url === '/api/v1/auth/login' && method === 'POST') return response(true, { access_token: 'tok-fin', full_name: 'Noah Silva' })
      if (url === '/api/v1/auth/me') return response(true, { role: 'finance', full_name: 'Noah Silva', organization_name: 'Seabreeze', user_id: 'u-fin' })
      if (url === '/api/v1/operations/overview') {
        return response(true, { open_folios: 1, active_orders: 0, pending_content: 0, open_complaints: 0, unread_releases: 0, pending_exports: 0 })
      }
      if (url === '/api/v1/folios') return response(true, [{ id: 'f1', room_number: '1208', guest_name: 'Maya Chen', status: 'open', balance_due: '12.00' }])
      if (url === '/api/v1/orders') return response(true, [])
      if (url === '/api/v1/content/releases') return response(true, [])
      if (url === '/api/v1/governance/lineage' && method === 'GET') return response(true, [])
      if (url === '/api/v1/governance/datasets' && method === 'POST') return response(true, { id: 'ds1' })
      if (url === '/api/v1/governance/lineage' && method === 'POST') return response(true, { status: 'ok' })
      if (url === '/api/v1/night-audit/run' && method === 'POST') return response(true, { status: 'ok', total_folios: 1, out_of_balance_folios: 0, imbalance_amount: '0.00', details: [] })
      if (url === '/api/v1/day-close/run' && method === 'POST') return response(true, { status: 'completed', business_date: '2026-03-29', organization_ids: ['org1'], runs: [] })
      if (url === '/api/v1/credit-score/calculate' && method === 'POST') return response(true, { username: 'guest@seabreeze.local', score: 710, violation_count: 0, last_rating: 5 })
      if (url.startsWith('/api/v1/credit-score/') && method === 'GET') {
        return response(true, { username: 'guest@seabreeze.local', score: 710, violation_count: 0, last_rating: 5, events: [] })
      }
      return response(true, [])
    })
    vi.stubGlobal('fetch', fetchMock)

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    wrapper.findComponent(LoginPanel).vm.$emit('submit', { username: 'finance@seabreeze.local', password: 'Harbor#2026!' })
    await flushPromises()

    wrapper.findComponent(FinanceClosePanel).vm.$emit('run-night-audit')
    wrapper.findComponent(FinanceClosePanel).vm.$emit('run-day-close')
    wrapper.findComponent(GovernanceOpsPanel).vm.$emit('create-dataset')
    wrapper.findComponent(GovernanceOpsPanel).vm.$emit('create-lineage')
    wrapper.findComponent(CreditPanel).vm.$emit('calculate-credit')
    await flushPromises()

    const calls = fetchMock.mock.calls.map((entry) => `${(entry[1]?.method || 'GET').toUpperCase()} ${entry[0]}`)
    expect(calls).toContain('POST /api/v1/night-audit/run')
    expect(calls).toContain('POST /api/v1/day-close/run')
    expect(calls).toContain('POST /api/v1/governance/datasets')
    expect(calls).toContain('POST /api/v1/governance/lineage')
    expect(calls).toContain('POST /api/v1/credit-score/calculate')
  })
})
