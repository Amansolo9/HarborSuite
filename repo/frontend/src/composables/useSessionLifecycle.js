import { ref } from 'vue'

export function useSessionLifecycle({
  session,
  loading,
  messages,
  api,
  router,
  clearMessages,
  onRefreshDashboard,
  onResetState,
}) {
  const lockoutSeconds = ref(0)
  const idleWarningSeconds = ref(0)

  let idleInterval = null
  let lockoutInterval = null
  let lastActivityAtMs = Date.now()

  function markActivity() {
    lastActivityAtMs = Date.now()
  }

  function stopIdleTracking() {
    if (idleInterval) {
      window.clearInterval(idleInterval)
      idleInterval = null
    }
    const handler = window.__harborsuiteIdleHandlers
    if (handler) {
      window.removeEventListener('mousemove', handler)
      window.removeEventListener('keydown', handler)
      window.removeEventListener('click', handler)
      document.removeEventListener('visibilitychange', handler)
      window.__harborsuiteIdleHandlers = null
    }
    idleWarningSeconds.value = 0
  }

  function startLockoutCountdown(seconds) {
    lockoutSeconds.value = Math.max(0, seconds)
    if (lockoutInterval) {
      window.clearInterval(lockoutInterval)
      lockoutInterval = null
    }
    if (lockoutSeconds.value === 0) {
      return
    }
    lockoutInterval = window.setInterval(() => {
      lockoutSeconds.value = Math.max(0, lockoutSeconds.value - 1)
      if (lockoutSeconds.value === 0 && lockoutInterval) {
        window.clearInterval(lockoutInterval)
        lockoutInterval = null
      }
    }, 1000)
  }

  function logout(showMessage = true) {
    api('/api/v1/auth/logout', { method: 'POST' }).catch(() => null)
    session.user = null
    session.overview = null
    onResetState()
    if (showMessage) {
      messages.success = 'Signed out.'
    }
    stopIdleTracking()
    router.push('/login')
  }

  function startIdleTracking() {
    stopIdleTracking()
    markActivity()
    const onActivity = () => markActivity()
    window.addEventListener('mousemove', onActivity)
    window.addEventListener('keydown', onActivity)
    window.addEventListener('click', onActivity)
    document.addEventListener('visibilitychange', onActivity)
    idleInterval = window.setInterval(() => {
      if (!session.user) {
        return
      }
      const elapsedMs = Date.now() - lastActivityAtMs
      const timeoutMinutes = Number(import.meta.env.VITE_SESSION_IDLE_MINUTES || 15)
      const timeoutMs = Math.max(1000, timeoutMinutes * 60 * 1000)
      const warnMs = Math.min(60 * 1000, Math.floor(timeoutMs / 2))
      if (elapsedMs >= timeoutMs) {
        logout(false)
        messages.error = `Session ended after ${timeoutMinutes} minutes of inactivity.`
        return
      }
      if (elapsedMs >= timeoutMs - warnMs) {
        const idleWarningUntilMs = lastActivityAtMs + timeoutMs
        idleWarningSeconds.value = Math.max(1, Math.floor((idleWarningUntilMs - Date.now()) / 1000))
      } else {
        idleWarningSeconds.value = 0
      }
    }, 1000)
    window.__harborsuiteIdleHandlers = onActivity
  }

  async function login(form) {
    clearMessages()
    if (lockoutSeconds.value > 0) {
      messages.error = `Account locked. Try again in ${lockoutSeconds.value}s.`
      return
    }
    loading.auth = true
    try {
      const payload = await api('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      startLockoutCountdown(0)
      await onRefreshDashboard()
      startIdleTracking()
      router.push('/workspace')
      messages.success = `Signed in as ${payload.full_name}.`
    } catch (error) {
      const text = String(error.message || '')
      const detail = error?.detail && typeof error.detail === 'object' ? error.detail : null
      const explicitLockout = Number(detail?.lockout_seconds ?? error?.retryAfterSeconds ?? 0)
      if (text.toLowerCase().includes('locked')) {
        startLockoutCountdown(Number.isFinite(explicitLockout) && explicitLockout > 0 ? explicitLockout : 15 * 60)
        messages.error = 'Account temporarily locked after repeated failed sign-in attempts.'
      } else {
        messages.error = text
      }
    } finally {
      loading.auth = false
    }
  }

  function onMountedSession() {
    return onRefreshDashboard()
      .then(() => {
        if (session.user) {
          startIdleTracking()
        }
      })
      .catch(() => Promise.resolve())
  }

  function onBeforeUnmountSession() {
    stopIdleTracking()
    if (lockoutInterval) {
      window.clearInterval(lockoutInterval)
      lockoutInterval = null
    }
  }

  return {
    lockoutSeconds,
    idleWarningSeconds,
    login,
    logout,
    onMountedSession,
    onBeforeUnmountSession,
    startIdleTracking,
    stopIdleTracking,
  }
}
