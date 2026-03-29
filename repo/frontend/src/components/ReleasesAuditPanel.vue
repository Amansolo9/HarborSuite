<template>
  <article class="panel wide">
    <div class="section-head">
      <div>
        <p class="eyebrow">Governance and evidence</p>
        <h2>Releases, complaints, and audit events</h2>
      </div>
    </div>
    <div class="split-grid">
      <div>
        <h3>Content releases</h3>
        <div class="stack-list">
          <div v-for="release in releases" :key="release.id" class="stack-card">
            <div>
              <strong>{{ release.title }}</strong>
              <p>{{ release.status }} · {{ release.content_type }} · roles {{ release.target_roles.join(', ') }} · orgs {{ (release.target_organizations || ['all']).join(', ') }} · reads {{ release.readership_count }}</p>
            </div>
            <div class="inline-actions" v-if="userRole === 'general_manager' && release.status === 'pending_approval'">
              <button class="ghost-button" @click="$emit('approve-release', release.id)">Approve</button>
            </div>
            <div class="inline-actions" v-if="['content_editor','general_manager'].includes(userRole)">
              <button class="ghost-button" @click="$emit('rollback-release', release.id)">Rollback</button>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3>Audit log</h3>
        <div class="stack-list audit-list">
          <div v-for="event in auditLogs" :key="event.id" class="stack-card">
            <strong>{{ event.action }}</strong>
            <p>{{ event.actor }} · {{ event.resource_type }} · {{ formatDate(event.created_at) }}</p>
          </div>
          <p v-if="!auditLogs.length" class="hint">Audit logs are available to general manager accounts.</p>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
defineProps({
  releases: { type: Array, required: true },
  auditLogs: { type: Array, required: true },
  userRole: { type: String, default: '' },
  formatDate: { type: Function, required: true },
})

defineEmits(['approve-release', 'rollback-release'])
</script>
