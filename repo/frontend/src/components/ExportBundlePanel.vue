<template>
  <article class="panel">
    <p class="eyebrow">Exports</p>
    <h2>Create checksum bundle</h2>
    <form class="form-grid" @submit.prevent="$emit('submit')">
      <label>
        Export type
        <input v-model="exportForm.export_type" required />
      </label>
      <label>
        Scope
        <input v-model="exportForm.scope" required />
      </label>
      <button class="primary-button" :disabled="loading">{{ loading ? 'Exporting...' : 'Create export' }}</button>
    </form>
    <p v-if="latestExport" class="hint">Latest checksum: {{ latestExport.checksum.slice(0, 16) }}...</p>
  </article>
</template>

<script setup>
defineProps({
  exportForm: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  latestExport: { type: Object, default: null },
})

defineEmits(['submit'])
</script>
