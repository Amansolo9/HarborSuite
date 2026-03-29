<template>
  <section class="content-grid">
    <article class="panel wide">
      <div class="section-head">
        <div>
          <p class="eyebrow">Operations KPI</p>
          <h2>Service duration metrics</h2>
        </div>
        <button class="ghost-button" :disabled="loading" @click="$emit('refresh')">{{ loading ? 'Loading...' : 'Refresh durations' }}</button>
      </div>
      <div class="stack-list" v-if="metrics.length">
        <div v-for="row in metrics.slice(0, 6)" :key="`${row.actor_role}-${row.order_type}`" class="stack-card">
          <strong>{{ row.actor_role }} · {{ row.order_type }}</strong>
          <p>{{ row.completed_orders }} orders · avg {{ row.avg_duration_minutes }} min</p>
        </div>
      </div>
      <p v-else class="hint">No completed service durations yet.</p>
    </article>
  </section>
</template>

<script setup>
defineProps({
  metrics: { type: Array, required: true },
  loading: { type: Boolean, default: false },
})
defineEmits(['refresh'])
</script>
