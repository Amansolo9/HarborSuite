<template>
  <article class="panel" v-if="selectedOrder">
    <p class="eyebrow">Service workflow</p>
    <h2>Order operations</h2>
    <p class="hint">Selected order: {{ selectedOrder.id }}</p>
    <form class="form-grid" @submit.prevent="$emit('transition-order')">
      <label>
        Next state
        <select v-model="orderOpsForm.next_state">
          <option value="confirmed">confirmed</option>
          <option value="in_prep">in_prep</option>
          <option value="delivered">delivered</option>
          <option value="canceled">canceled</option>
          <option value="refunded">refunded</option>
        </select>
      </label>
      <label>
        Reversal reason
        <input v-model="orderOpsForm.reversal_reason" placeholder="Required for refunded" />
      </label>
      <button class="primary-button" :disabled="actionLoading.orderTransition">{{ actionLoading.orderTransition ? 'Updating...' : 'Transition order' }}</button>
    </form>

    <form class="form-grid" @submit.prevent="$emit('split-order')">
      <label class="full-span">
        Split rows (`supplier|warehouse|sla|qty`; semicolon separated)
        <input v-model="orderOpsForm.split_allocations" />
      </label>
      <button class="ghost-button" :disabled="actionLoading.orderSplit">{{ actionLoading.orderSplit ? 'Splitting...' : 'Split allocations' }}</button>
    </form>

    <form class="form-grid" @submit.prevent="$emit('merge-order')">
      <label><input v-model="orderOpsForm.merge_supplier" required /></label>
      <label><input v-model="orderOpsForm.merge_warehouse" required /></label>
      <label><input v-model="orderOpsForm.merge_sla_tier" required /></label>
      <button class="ghost-button" :disabled="actionLoading.orderMerge">{{ actionLoading.orderMerge ? 'Merging...' : 'Merge allocations' }}</button>
    </form>
  </article>
</template>

<script setup>
defineProps({
  selectedOrder: { type: Object, default: null },
  orderOpsForm: { type: Object, required: true },
  actionLoading: { type: Object, required: true },
})

defineEmits(['transition-order', 'split-order', 'merge-order'])
</script>
