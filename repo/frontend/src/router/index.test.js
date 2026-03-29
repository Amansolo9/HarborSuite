import { describe, expect, it, vi } from 'vitest'

import { resolveNavigation } from './index'

describe('router guards', () => {
  it('redirects unauthenticated protected route to login', async () => {
    vi.stubGlobal('fetch', async () => ({ ok: false }))
    const result = await resolveNavigation({ meta: { requiresAuth: true } })
    expect(result).toBe('/login')
  })

  it('blocks route when server role is not allowed', async () => {
    vi.stubGlobal('fetch', async () => ({
      ok: true,
      json: async () => ({ role: 'guest' }),
    }))
    const result = await resolveNavigation({ meta: { requiresAuth: true, roles: ['finance'] } })
    expect(result).toBe('/workspace')
  })
})
