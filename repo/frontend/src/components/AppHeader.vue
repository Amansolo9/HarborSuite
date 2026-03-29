<template>
  <header class="topbar">
    <div>
      <p class="eyebrow">Offline hotel commerce and PMS</p>
      <h1>HarborSuite Control Deck</h1>
    </div>
    <div v-if="sessionUser" class="session-card">
      <strong>{{ sessionUser.full_name }}</strong>
      <span>{{ readableRole(sessionUser.role) }} · {{ sessionUser.organization_name }}</span>
      <small v-if="idleWarningSeconds > 0" class="hint">Idle timeout in {{ idleWarningSeconds }}s</small>
      <button class="ghost-button" @click="$emit('logout')">Sign out</button>
    </div>
  </header>
</template>

<script setup>
defineProps({
  sessionUser: { type: Object, default: null },
  idleWarningSeconds: { type: Number, default: 0 },
  readableRole: { type: Function, required: true },
})

defineEmits(['logout'])
</script>
