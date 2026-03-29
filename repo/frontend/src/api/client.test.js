import { describe, expect, it, vi } from 'vitest'

import { createApiClient } from './client'

describe('api client', () => {
  it('injects auth header when token exists', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ ok: true }),
    }))
    vi.stubGlobal('fetch', fetchMock)
    const api = createApiClient({ baseUrl: 'http://localhost:8000', getToken: () => 'token-1' })

    await api('/api/v1/auth/me')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer token-1')
    expect(options.credentials).toBe('include')
  })

  it('throws parsed error details on failure', async () => {
    vi.stubGlobal('fetch', async () => ({
      ok: false,
      json: async () => ({ detail: 'nope' }),
    }))
    const api = createApiClient({ baseUrl: 'http://localhost:8000', getToken: () => '' })

    await expect(api('/api/v1/orders')).rejects.toThrow('nope')
  })
})
