<template>
  <article class="panel" v-if="selectedOrder">
    <p class="eyebrow">Post-service feedback</p>
    <h2>Ratings</h2>
    <form class="form-grid" @submit.prevent="$emit('submit')">
      <label>
        Target username
        <input v-model="ratingForm.to_username" required />
      </label>
      <label>
        Score
        <input v-model.number="ratingForm.score" type="number" min="1" max="5" required />
      </label>
      <label class="full-span">
        Comment
        <input v-model="ratingForm.comment" />
      </label>
      <label class="full-span">
        Order ID
        <input v-model="ratingForm.order_id" required />
      </label>
      <button class="primary-button" :disabled="submitting">{{ submitting ? 'Submitting...' : 'Submit rating' }}</button>
    </form>
    <div class="stack-list" v-if="ratings.length">
      <div v-for="row in ratings.slice(0, 5)" :key="row.id" class="stack-card">
        <strong>{{ row.score }}★</strong>
        <p>{{ row.order_id }} · {{ formatDate(row.created_at) }}</p>
      </div>
    </div>
  </article>
</template>

<script setup>
defineProps({
  selectedOrder: { type: Object, default: null },
  ratingForm: { type: Object, required: true },
  ratings: { type: Array, required: true },
  formatDate: { type: Function, required: true },
  submitting: { type: Boolean, default: false },
})

defineEmits(['submit'])
</script>
