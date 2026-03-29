export function useDisplayUtils(canViewSensitiveNotes) {
  function readableRole(role) {
    return String(role || '').replaceAll('_', ' ')
  }

  function formatDate(value) {
    return new Date(value).toLocaleString()
  }

  function maskReceiptLine(line) {
    if (canViewSensitiveNotes.value) {
      return line
    }
    const parts = String(line).split(' ')
    if (parts.length <= 4) {
      return line
    }
    const prefix = parts.slice(0, 4).join(' ')
    const tail = parts.slice(4).join(' ')
    if (tail.length <= 6) {
      return `${prefix} ***`
    }
    return `${prefix} ${tail.slice(0, 2)}${'*'.repeat(Math.max(1, tail.length - 4))}${tail.slice(-2)}`
  }

  function maskSensitiveText(value) {
    const text = String(value || '')
    if (canViewSensitiveNotes.value) {
      return text
    }
    if (text.length <= 6) {
      return '***'
    }
    return `${text.slice(0, 2)}${'*'.repeat(Math.max(1, text.length - 4))}${text.slice(-2)}`
  }

  return {
    readableRole,
    formatDate,
    maskReceiptLine,
    maskSensitiveText,
  }
}
