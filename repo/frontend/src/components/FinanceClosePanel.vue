<template>
  <article class="panel">
    <p class="eyebrow">Finance controls</p>
    <h2>Night audit and day-close</h2>
    <form class="form-grid" @submit.prevent="$emit('run-night-audit')">
      <label class="checkbox-row full-span">
        <input v-model="nightAuditForm.all_organizations" type="checkbox" />
        Run night audit for all organizations (super-admin only)
      </label>
      <button class="primary-button" :disabled="nightAuditLoading">{{ nightAuditLoading ? 'Running...' : 'Run night audit' }}</button>
    </form>
    <form class="form-grid" @submit.prevent="$emit('run-day-close')">
      <label>
        Business date (optional)
        <input v-model="closeForm.business_date" placeholder="YYYY-MM-DD" />
      </label>
      <label class="checkbox-row">
        <input v-model="closeForm.all_organizations" type="checkbox" />
        All organizations
      </label>
      <button class="ghost-button" :disabled="dayCloseLoading">{{ dayCloseLoading ? 'Running...' : 'Run day-close' }}</button>
    </form>
    <p v-if="nightAuditResult" class="hint">Night audit: {{ nightAuditResult.failed_count }} failed of {{ nightAuditResult.total_folios }}</p>
    <p v-if="dayCloseResult" class="hint">Day-close: {{ dayCloseResult.passed ? 'passed' : 'failed' }} · runs {{ dayCloseResult.runs.length }}</p>
  </article>
</template>

<script setup>
defineProps({
  nightAuditForm: { type: Object, required: true },
  closeForm: { type: Object, required: true },
  nightAuditResult: { type: Object, default: null },
  dayCloseResult: { type: Object, default: null },
  nightAuditLoading: { type: Boolean, default: false },
  dayCloseLoading: { type: Boolean, default: false },
})

defineEmits(['run-night-audit', 'run-day-close'])
</script>
