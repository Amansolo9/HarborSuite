<template>
  <article class="panel" v-if="pendingQuote">
    <p class="eyebrow">Quote reconfirmation</p>
    <h2>Confirm quoted totals before submit</h2>
    <p class="hint">Quote hash {{ pendingQuote.quote_hash.slice(0, 12) }}... expires {{ formatDate(quoteExpiryDisplay || pendingQuote.expires_at) }}</p>
    <p class="hint">Orders must be submitted within 10 minutes of quote confirmation.</p>
    <div class="inline-actions">
      <button class="primary-button" :disabled="quoteExpired" @click="$emit('submit-confirmed')">{{ quoteExpired ? 'Quote expired' : 'Submit confirmed order' }}</button>
      <button class="ghost-button" @click="$emit('discard')">Discard quote</button>
    </div>
    <p v-if="quoteExpired" class="hint">Quote expired. Reconfirm pricing and taxes before submit.</p>
  </article>
</template>

<script setup>
defineProps({
  pendingQuote: { type: Object, default: null },
  quoteExpiryDisplay: { type: String, default: '' },
  quoteExpired: { type: Boolean, default: false },
  formatDate: { type: Function, required: true },
})

defineEmits(['submit-confirmed', 'discard'])
</script>
