<template>
  <article class="panel">
    <p class="eyebrow">Data governance</p>
    <h2>Dataset and lineage operations</h2>
    <form class="form-grid" @submit.prevent="$emit('create-dataset')">
      <label><input v-model="datasetForm.dataset_name" placeholder="dataset name" required /></label>
      <label><input v-model="datasetForm.version" placeholder="version" required /></label>
      <label class="full-span">
        Dataset schema JSON
        <textarea v-model="datasetForm.dataset_schema_json" rows="3" required />
      </label>
      <button class="primary-button" :disabled="datasetLoading">{{ datasetLoading ? 'Registering...' : 'Register dataset' }}</button>
    </form>
    <form class="form-grid" @submit.prevent="$emit('create-lineage')">
      <label><input v-model="lineageForm.metric_name" placeholder="metric" required /></label>
      <label><input v-model="lineageForm.dataset_version_id" placeholder="dataset version id" required /></label>
      <label><input v-model="lineageForm.source_tables_csv" placeholder="orders,folios" required /></label>
      <label><input v-model="lineageForm.source_query_ref" placeholder="query ref" required /></label>
      <button class="ghost-button" :disabled="lineageLoading">{{ lineageLoading ? 'Registering...' : 'Register lineage' }}</button>
    </form>
    <div class="stack-list" v-if="lineageRows.length">
      <div v-for="row in lineageRows.slice(0, 5)" :key="row.id" class="stack-card">
        <strong>{{ row.metric_name }}</strong>
        <p>{{ row.dataset_version_id }} · {{ row.source_tables.join(', ') }}</p>
      </div>
    </div>
  </article>
</template>

<script setup>
defineProps({
  datasetForm: { type: Object, required: true },
  lineageForm: { type: Object, required: true },
  lineageRows: { type: Array, required: true },
  datasetLoading: { type: Boolean, default: false },
  lineageLoading: { type: Boolean, default: false },
})

defineEmits(['create-dataset', 'create-lineage'])
</script>
