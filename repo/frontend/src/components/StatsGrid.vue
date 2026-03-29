<template>
  <section class="stats-grid">
    <article v-for="stat in stats" :key="stat.label" class="stat-card">
      <span>{{ stat.label }}</span>
      <strong>{{ stat.value }}</strong>
      <small>{{ stat.note }}</small>
    </article>
  </section>
</template>

<script setup>
defineProps({
  stats: { type: Array, required: true },
})
</script>
