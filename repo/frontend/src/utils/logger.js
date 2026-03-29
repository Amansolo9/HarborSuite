const REDACT_KEYS = new Set(['password', 'token', 'authorization', 'access_token', 'refresh_token'])
const IS_DEV = import.meta.env.DEV

function redact(value, keyHint = '') {
  if (value === null || value === undefined) {
    return value
  }
  const hint = String(keyHint || '').toLowerCase()
  if (REDACT_KEYS.has(hint)) {
    return '[redacted]'
  }
  if (Array.isArray(value)) {
    return value.map((entry) => redact(entry))
  }
  if (typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, redact(entry, key)]))
  }
  if (typeof value === 'string' && hint.includes('auth')) {
    return '[redacted]'
  }
  return value
}

export function logClientEvent(level, category, message, context = {}) {
  if (!IS_DEV) {
    return
  }
  const line = `[harborsuite:${category}] ${message}`
  const payload = redact(context)
  if (level === 'error') {
    console.error(line, payload)
    return
  }
  if (level === 'warn') {
    console.warn(line, payload)
    return
  }
  console.info(line, payload)
}
