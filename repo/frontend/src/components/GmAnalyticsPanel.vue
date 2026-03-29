<template>
  <article class="panel wide">
    <div class="section-head">
      <div>
        <p class="eyebrow">General manager analytics</p>
        <h2>Scale, churn, participation, fund, and approval metrics</h2>
      </div>
      <button class="ghost-button" :disabled="loading" @click="$emit('refresh')">{{ loading ? 'Loading...' : 'Refresh dashboard' }}</button>
    </div>

    <div class="stats-grid" v-if="metrics">
      <article class="stat-card" v-for="item in metricCards" :key="item.label">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </article>
    </div>
    <p v-else class="hint">No analytics snapshot yet.</p>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  metrics: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

defineEmits(['refresh'])

const metricCards = computed(() => {
  if (!props.metrics) {
    return []
  }
  return [
    { label: 'Scale index', value: props.metrics.scale_index, note: 'member scale indicator' },
    { label: 'Churn rate', value: `${props.metrics.churn_rate}%`, note: 'member churn' },
    { label: 'Participation', value: `${props.metrics.participation_rate}%`, note: 'event participation' },
    { label: 'Order volume', value: props.metrics.order_volume, note: 'event volume' },
    { label: 'Fund net', value: props.metrics.fund_income_expense, note: 'income-expense net' },
    { label: 'Budget execution', value: `${props.metrics.budget_execution}%`, note: 'budget progress' },
    { label: 'Approval efficiency', value: `${props.metrics.approval_efficiency}%`, note: 'content approvals' },
  ]
})
</script>
