<template>
  <article class="panel">
    <p class="eyebrow">Content governance</p>
    <h2>Create release</h2>
    <form class="form-grid" @submit.prevent="$emit('submit')">
      <label>
        Title
        <input v-model="releaseForm.title" required />
      </label>
      <label>
        Target tags (comma-separated)
        <input v-model="releaseForm.tags_csv" required placeholder="vip,conference" />
      </label>
      <label>
        Target organization IDs
        <input v-model="releaseForm.organizations" placeholder="all or comma-separated org ids" required />
      </label>
      <label class="full-span">
        Body
        <textarea v-model="releaseForm.body" required rows="4"></textarea>
      </label>
      <label>
        Target roles (comma-separated)
        <input v-model="releaseForm.roles_csv" required placeholder="guest,front_desk" />
      </label>
      <label>
        Content type
        <select v-model="releaseForm.content_type">
          <option value="announcement">announcement</option>
          <option value="news">news</option>
          <option value="carousel_promo">carousel_promo</option>
        </select>
      </label>
      <button class="primary-button" :disabled="loading">{{ loading ? 'Saving...' : 'Create release' }}</button>
    </form>
  </article>
</template>

<script setup>
defineProps({
  releaseForm: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})
defineEmits(['submit'])
</script>
