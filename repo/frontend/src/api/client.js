import { logClientEvent } from '../utils/logger'

export function createApiClient({ baseUrl, getToken }) {
  return async function api(path, options = {}) {
    const optionHeaders = options.headers || {}
    const token = getToken()
    const method = (options.method || 'GET').toUpperCase()
    let response
    try {
      response = await fetch(`${baseUrl}${path}`, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...optionHeaders,
        },
      })
    } catch (error) {
      logClientEvent('error', 'network', 'request failed before response', {
        method,
        path,
        error: String(error?.message || error),
      })
      throw error
    }

    if (response.status === 204) {
      return null
    }

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = data.detail
      const detailMessage = Array.isArray(detail)
        ? detail.map((entry) => entry.msg || JSON.stringify(entry)).join('; ')
        : typeof detail === 'object' && detail !== null
          ? String(detail.message || detail.error || 'Request failed.')
          : detail
      const retryAfterHeader = response.headers?.get ? response.headers.get('Retry-After') : null
      const retryAfterSeconds = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : null
      logClientEvent('warn', 'api', 'non-success response', {
        method,
        path,
        status: response.status,
        hasDetail: Boolean(detail),
      })
      const error = new Error(detailMessage || 'Request failed.')
      error.status = response.status
      error.detail = detail
      if (Number.isFinite(retryAfterSeconds)) {
        error.retryAfterSeconds = retryAfterSeconds
      }
      throw error
    }
    return data
  }
}
