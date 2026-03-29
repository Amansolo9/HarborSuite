<template>
  <article class="panel" v-if="selectedFolio">
    <p class="eyebrow">Front desk and finance</p>
    <h2>Folio operations</h2>
    <form class="form-grid" @submit.prevent="$emit('post-charge')">
      <label>
        Charge amount
        <input v-model="folioChargeForm.amount" type="number" min="0.01" step="0.01" required />
      </label>
      <label>
        Method
        <select v-model="folioChargeForm.payment_method">
          <option value="cash">cash</option>
          <option value="card_present_manual">card_present_manual</option>
          <option value="gift_certificate">gift_certificate</option>
          <option value="direct_bill">direct_bill</option>
        </select>
      </label>
      <label class="full-span">
        Charge reason (required)
        <input v-model="folioChargeForm.reason" required />
      </label>
      <button class="primary-button" :disabled="actionLoading.folioCharge">{{ actionLoading.folioCharge ? 'Posting...' : 'Post manual charge' }}</button>
    </form>

    <form class="form-grid" @submit.prevent="$emit('post-payment')">
      <label>
        Payment amount
        <input v-model="folioPaymentForm.amount" type="number" min="0.01" step="0.01" required />
      </label>
      <label>
        Method
        <select v-model="folioPaymentForm.payment_method">
          <option value="cash">cash</option>
          <option value="card_present_manual">card_present_manual</option>
          <option value="gift_certificate">gift_certificate</option>
          <option value="direct_bill">direct_bill</option>
        </select>
      </label>
      <label class="full-span">
        Payment note
        <input v-model="folioPaymentForm.note" />
      </label>
      <button class="primary-button" :disabled="actionLoading.folioPayment">{{ actionLoading.folioPayment ? 'Posting...' : 'Post payment' }}</button>
    </form>

    <form class="form-grid" @submit.prevent="$emit('post-reversal')">
      <label>
        Reversal amount
        <input v-model="folioReversalForm.amount" type="number" min="0.01" step="0.01" required />
      </label>
      <label>
        Reason
        <input v-model="folioReversalForm.reason" required />
      </label>
      <button class="ghost-button" :disabled="actionLoading.folioReversal">{{ actionLoading.folioReversal ? 'Posting...' : 'Post reversal' }}</button>
    </form>

    <form class="form-grid" @submit.prevent="$emit('split-folio')">
      <label class="full-span">
        Split allocations (comma separated)
        <input v-model="folioSplitForm.allocations" placeholder="20.00,30.00" />
      </label>
      <button class="ghost-button" :disabled="actionLoading.folioSplit">{{ actionLoading.folioSplit ? 'Splitting...' : 'Split folio' }}</button>
    </form>

    <form class="form-grid" @submit.prevent="$emit('merge-folios')">
      <label>
        Primary folio ID
        <input v-model="folioMergeForm.primary_folio_id" required />
      </label>
      <label>
        Secondary folio ID
        <input v-model="folioMergeForm.secondary_folio_id" required />
      </label>
      <button class="ghost-button" :disabled="actionLoading.folioMerge">{{ actionLoading.folioMerge ? 'Merging...' : 'Merge folios' }}</button>
    </form>

    <div class="inline-actions">
      <button class="ghost-button" :disabled="actionLoading.folioReceipt" @click="$emit('load-receipt')">{{ actionLoading.folioReceipt ? 'Loading...' : 'Load receipt' }}</button>
      <button class="ghost-button" :disabled="actionLoading.folioInvoice" @click="$emit('load-invoice')">{{ actionLoading.folioInvoice ? 'Loading...' : 'Load invoice' }}</button>
      <button class="ghost-button" :disabled="actionLoading.folioPrint" @click="$emit('queue-print')">{{ actionLoading.folioPrint ? 'Queueing...' : 'Queue print' }}</button>
      <button class="ghost-button" :disabled="actionLoading.folioPrintInvoice" @click="$emit('queue-print-invoice')">{{ actionLoading.folioPrintInvoice ? 'Queueing...' : 'Queue invoice print' }}</button>
    </div>

    <div v-if="receiptPreview" class="stack-card">
      <strong>Receipt preview</strong>
      <p>{{ receiptPreview.guest_name }} · room {{ receiptPreview.room_number }} · due {{ receiptPreview.balance_due }}</p>
      <p v-for="line in receiptPreview.printable_lines.slice(0, 6)" :key="line">{{ maskReceiptLine(line) }}</p>
    </div>

    <div v-if="invoicePreview" class="stack-card">
      <strong>Invoice preview</strong>
      <p>{{ invoicePreview.invoice_id }} · {{ invoicePreview.guest_name }} · room {{ invoicePreview.room_number }}</p>
      <p v-for="line in invoicePreview.invoice_lines.slice(0, 6)" :key="line">{{ maskSensitiveText(line) }}</p>
    </div>

    <p v-if="printJob" class="hint">Print job {{ printJob.print_job_id }} queued at {{ printJob.queue_path }}</p>
  </article>
</template>

<script setup>
defineProps({
  selectedFolio: { type: Object, default: null },
  folioChargeForm: { type: Object, required: true },
  folioPaymentForm: { type: Object, required: true },
  folioReversalForm: { type: Object, required: true },
  folioSplitForm: { type: Object, required: true },
  folioMergeForm: { type: Object, required: true },
  actionLoading: { type: Object, required: true },
  receiptPreview: { type: Object, default: null },
  invoicePreview: { type: Object, default: null },
  printJob: { type: Object, default: null },
  maskReceiptLine: { type: Function, required: true },
  maskSensitiveText: { type: Function, required: true },
})

defineEmits([
  'post-charge',
  'post-payment',
  'post-reversal',
  'split-folio',
  'merge-folios',
  'load-receipt',
  'load-invoice',
  'queue-print',
  'queue-print-invoice',
])
</script>
