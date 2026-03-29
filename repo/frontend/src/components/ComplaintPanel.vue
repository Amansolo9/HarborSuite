<template>
  <article class="panel" v-if="selectedFolio">
    <p class="eyebrow">Guest relations</p>
    <h2>File complaint</h2>
    <form class="form-grid" @submit.prevent="$emit('submit')">
      <label>
        Subject
        <input v-model="complaintForm.subject" required />
      </label>
      <label>
        Rating
        <input v-model.number="complaintForm.service_rating" min="1" max="5" type="number" required />
      </label>
      <label class="full-span">
        Detail
        <textarea v-model="complaintForm.detail" required rows="4"></textarea>
      </label>
      <label class="checkbox-row full-span">
        <input v-model="complaintForm.violation_flag" type="checkbox" />
        Flag as policy or conduct violation
      </label>
      <button class="primary-button" :disabled="loading || !eligibility.eligible">{{ loading ? 'Saving...' : 'Create complaint' }}</button>
    </form>
    <p class="hint">{{ eligibility.reason }}</p>
    <div class="inline-actions" v-if="lastComplaintId">
      <button class="ghost-button" @click="$emit('export-packet')">Export complaint packet</button>
      <a
        v-if="complaintPacket"
        class="ghost-button"
        :href="complaintPacket.download_url"
        :download="complaintPacket.packet_filename"
        target="_blank"
        rel="noopener noreferrer"
      >
        Download/Open PDF
      </a>
      <p v-if="complaintPacket" class="hint">Packet checksum: {{ complaintPacket.checksum.slice(0, 16) }}...</p>
    </div>
    <div v-if="complaintPacket" class="stack-list">
      <article class="stack-card">
        <strong>{{ complaintPacket.packet_filename }}</strong>
        <p>Type: {{ complaintPacket.packet_media_type }}</p>
        <p>Packet path: {{ complaintPacket.packet_path }}</p>
        <p>Manifest path: {{ complaintPacket.manifest_path }}</p>
      </article>
    </div>
  </article>
</template>

<script setup>
defineProps({
  selectedFolio: { type: Object, default: null },
  complaintForm: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  eligibility: { type: Object, required: true },
  lastComplaintId: { type: String, default: '' },
  complaintPacket: { type: Object, default: null },
})
defineEmits(['submit', 'export-packet'])
</script>
