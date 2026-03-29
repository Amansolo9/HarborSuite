<template>
  <article class="panel">
    <p class="eyebrow">Credit operations</p>
    <h2>Credit score and violations</h2>
    <form class="form-grid" @submit.prevent="$emit('calculate-credit')">
      <label>
        Username
        <input v-model="creditForm.username" required />
      </label>
      <label>
        Rating
        <input v-model.number="creditForm.rating" type="number" min="1" max="5" required />
      </label>
      <label>
        Penalty amount
        <input v-model="creditForm.penalty" type="number" min="0" step="0.01" />
      </label>
      <label class="checkbox-row">
        <input v-model="creditForm.violation" type="checkbox" />
        Violation event
      </label>
      <label class="full-span">
        Note
        <input v-model="creditForm.note" />
      </label>
      <button class="primary-button" :disabled="calculateLoading">{{ calculateLoading ? 'Updating...' : 'Update credit score' }}</button>
    </form>
    <div class="inline-actions">
      <input :value="creditLookupUsername" placeholder="username to view profile" @input="$emit('update:creditLookupUsername', $event.target.value)" />
      <button class="ghost-button" :disabled="loadProfileLoading" @click="$emit('load-profile')">{{ loadProfileLoading ? 'Loading...' : 'Load profile' }}</button>
    </div>
    <div v-if="creditProfile" class="stack-list">
      <div class="stack-card">
        <strong>{{ creditProfile.username }} score {{ creditProfile.score }}</strong>
        <p>Violations {{ creditProfile.violation_count }} · last rating {{ creditProfile.last_rating }}</p>
      </div>
      <div v-for="event in creditProfile.events.slice(0, 5)" :key="`${event.created_at}-${event.rating}`" class="stack-card">
        <strong>Rating {{ event.rating }} · Penalty {{ event.penalty }}</strong>
        <p>{{ event.created_at }} · violation {{ event.violation }} · {{ maskSensitiveText(event.note) }}</p>
      </div>
    </div>
  </article>
</template>

<script setup>
defineProps({
  creditForm: { type: Object, required: true },
  creditLookupUsername: { type: String, required: true },
  creditProfile: { type: Object, default: null },
  maskSensitiveText: { type: Function, required: true },
  calculateLoading: { type: Boolean, default: false },
  loadProfileLoading: { type: Boolean, default: false },
})

defineEmits(['calculate-credit', 'load-profile', 'update:creditLookupUsername'])
</script>
