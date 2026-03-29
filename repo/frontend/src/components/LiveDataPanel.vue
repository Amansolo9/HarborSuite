<template>
  <article class="panel wide">
    <div class="section-head">
      <div>
        <p class="eyebrow">Live property data</p>
        <h2>Folios and orders</h2>
      </div>
      <button class="ghost-button" @click="$emit('refresh')">Refresh</button>
    </div>

    <div class="split-grid">
      <div>
        <h3>Folios</h3>
        <div class="table-card">
          <div class="table-row header-row">
            <span>Room</span>
            <span>Guest</span>
            <span>Status</span>
            <span>Balance</span>
          </div>
          <div v-for="folio in folios" :key="folio.id" class="table-row selectable" @click="$emit('select-folio', folio)">
            <span>{{ folio.room_number }}</span>
            <span>{{ folio.guest_name }}</span>
            <span>{{ folio.status }}</span>
            <span>${{ folio.balance_due }}</span>
          </div>
          <div v-if="loading" class="table-row">
            <span>Loading folios...</span>
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div v-else-if="!folios.length" class="table-row">
            <span>No folios available.</span>
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>

      <div>
        <h3>Orders</h3>
        <div class="table-card">
          <div class="table-row header-row five-col">
            <span>ID</span>
            <span>State</span>
            <span>Method</span>
            <span>Total</span>
            <span>Tax by</span>
          </div>
          <div v-for="order in orders" :key="order.id" class="table-row five-col selectable" @click="$emit('select-order', order)">
            <span>{{ order.id.slice(0, 8) }}</span>
            <span>{{ order.state }}</span>
            <span>{{ order.payment_method }}</span>
            <span>${{ order.total_amount }}</span>
            <span>{{ formatDate(order.tax_reconfirm_by) }}</span>
          </div>
          <div v-if="loading" class="table-row five-col">
            <span>Loading orders...</span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div v-else-if="!orders.length" class="table-row five-col">
            <span>No orders available.</span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
defineProps({
  folios: { type: Array, required: true },
  orders: { type: Array, required: true },
  formatDate: { type: Function, required: true },
  loading: { type: Boolean, default: false },
})

defineEmits(['refresh', 'select-folio', 'select-order'])
</script>
