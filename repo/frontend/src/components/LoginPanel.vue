<template>
  <section class="login-layout">
    <article class="panel intro-panel">
      <p class="eyebrow">Review findings addressed</p>
      <h2>Real API + real role workflows</h2>
      <p>
        Sign in with one of the seeded hotel roles to exercise order flow, folios,
        content governance, complaints, exports, and audit logs against the API.
      </p>
      <ul>
        <li><strong>Guest</strong> `guest@seabreeze.local`</li>
        <li><strong>Front desk</strong> `desk@seabreeze.local`</li>
        <li><strong>Service</strong> `service@seabreeze.local`</li>
        <li><strong>Finance</strong> `finance@seabreeze.local`</li>
        <li><strong>Editor</strong> `editor@seabreeze.local`</li>
        <li><strong>GM</strong> `gm@seabreeze.local`</li>
      </ul>
      <p class="hint">Use your issued role credentials.</p>
    </article>

    <article class="panel form-panel">
      <p class="eyebrow">Role sign-in</p>
      <h2>Start a session</h2>
      <form class="form-grid" @submit.prevent="submit">
        <label>
          Username
          <input v-model="form.username" required type="email" />
        </label>
        <label>
          Password
          <input v-model="form.password" required type="password" />
        </label>
        <p class="hint full-span">Password policy: at least 10 chars with upper, lower, number, and symbol.</p>
        <p v-if="validationError" class="message error full-span">{{ validationError }}</p>
        <p v-if="lockoutSeconds > 0" class="message error full-span">Account locked. Try again in {{ lockoutSeconds }}s.</p>
        <button class="primary-button" :disabled="loading || lockoutSeconds > 0">
          {{ loading ? 'Signing in...' : lockoutSeconds > 0 ? 'Locked' : 'Sign in' }}
        </button>
      </form>
      <p v-if="!validationError && error" class="message error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  lockoutSeconds: { type: Number, default: 0 },
})

const emit = defineEmits(['submit'])

const form = reactive({ username: '', password: '' })
const validationError = ref('')

function validPassword(value) {
  const text = String(value || '')
  return text.length >= 10 && /[A-Z]/.test(text) && /[a-z]/.test(text) && /\d/.test(text) && /[^A-Za-z0-9]/.test(text)
}

function submit() {
  validationError.value = ''
  if (!validPassword(form.password)) {
    validationError.value = 'Password must be 10+ chars with upper, lower, number, and symbol.'
    return
  }
  emit('submit', { ...form })
}
</script>
