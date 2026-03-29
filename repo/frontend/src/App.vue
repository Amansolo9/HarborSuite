<template>
  <div class="shell">
    <AppHeader :session-user="session.user" :idle-warning-seconds="idleWarningSeconds" :readable-role="readableRole" @logout="logout" />

    <LoginPanel v-if="!session.user" :loading="loading.auth" :error="messages.error" :lockout-seconds="lockoutSeconds" @submit="login" />

    <template v-else>
      <StatsGrid :stats="stats" />

      <section class="content-grid" v-if="canSeeGmDashboard && showOpsDomain">
        <GmAnalyticsPanel :metrics="gmDashboardMetrics" :loading="loading.gmDashboard" @refresh="loadGmDashboard" />
      </section>

      <ServiceDurationPanel v-if="canSeeServiceDurations && showOpsDomain" :metrics="serviceDurationMetrics" :loading="loading.serviceDuration" @refresh="loadServiceDurations" />

      <section class="content-grid">
        <LiveDataPanel v-if="showOpsDomain" :folios="folios" :orders="orders" :format-date="formatDate" :loading="loading.dashboard" @refresh="refreshDashboard" @select-folio="selectFolio" @select-order="selectOrder" />

        <OrderComposer v-if="isWorkspaceScope && canCreateOrder && selectedFolio" :loading="loading.order" :selected-folio="selectedFolio" @submit="createOrder" />

        <QuoteReconfirmPanel
          v-if="isWorkspaceScope && pendingQuote && canCreateOrder && selectedFolio"
          :pending-quote="pendingQuote"
          :quote-expiry-display="quoteExpiryDisplay"
          :quote-expired="quoteExpired"
          :format-date="formatDate"
          @submit-confirmed="submitConfirmedOrder"
          @discard="clearPendingQuote"
        />

        <ComplaintPanel
          v-if="isWorkspaceScope && canFileComplaint"
          :selected-folio="selectedFolio"
          :complaint-form="complaintForm"
          :loading="loading.complaint"
          :eligibility="complaintEligibility"
          :last-complaint-id="lastComplaintId"
          :complaint-packet="complaintPacket"
          @submit="createComplaint"
          @export-packet="exportComplaintPacket"
        />

        <ContentReleasePanel v-if="showGovernanceDomain && canManageContent" :release-form="releaseForm" :loading="loading.release" @submit="createRelease" />

        <ExportBundlePanel v-if="showOpsDomain && canExport" :export-form="exportForm" :loading="loading.exportBundle" :latest-export="latestExport" @submit="createExportBundle" />

        <FolioOperationsPanel
          v-if="showOpsDomain && canManageFolios"
          :selected-folio="selectedFolio"
          :folio-charge-form="folioChargeForm"
          :folio-payment-form="folioPaymentForm"
          :folio-reversal-form="folioReversalForm"
          :folio-split-form="folioSplitForm"
          :folio-merge-form="folioMergeForm"
          :action-loading="actionLoading"
          :receipt-preview="receiptPreview"
          :invoice-preview="invoicePreview"
          :print-job="printJob"
          :mask-receipt-line="maskReceiptLine"
          :mask-sensitive-text="maskSensitiveText"
          @post-charge="postFolioCharge"
          @post-payment="postFolioPayment"
          @post-reversal="postFolioReversal"
          @split-folio="splitFolioBill"
          @merge-folios="mergeFoliosBill"
          @load-receipt="loadFolioReceipt"
          @load-invoice="loadFolioInvoice"
          @queue-print="queueFolioPrint"
          @queue-print-invoice="queueFolioInvoicePrint"
        />

        <OrderOperationsPanel
          v-if="showOpsDomain && canOperateOrders"
          :selected-order="selectedOrder"
          :order-ops-form="orderOpsForm"
          :action-loading="actionLoading"
          @transition-order="transitionOrderState"
          @split-order="splitOrderDims"
          @merge-order="mergeOrderDims"
        />

        <RatingsPanel v-if="isWorkspaceScope && canRate" :selected-order="selectedOrder" :rating-form="ratingForm" :ratings="ratings" :format-date="formatDate" :submitting="backofficeLoading.submitRating" @submit="submitRating" />

        <GovernanceOpsPanel v-if="showGovernanceDomain && canGovernance" :dataset-form="datasetForm" :lineage-form="lineageForm" :lineage-rows="lineageRows" :dataset-loading="backofficeLoading.createDataset" :lineage-loading="backofficeLoading.createLineage" @create-dataset="createDataset" @create-lineage="createLineage" />

        <FinanceClosePanel v-if="showOpsDomain && canRunClose" :night-audit-form="nightAuditForm" :close-form="closeForm" :night-audit-result="nightAuditResult" :day-close-result="dayCloseResult" :night-audit-loading="backofficeLoading.runNightAudit" :day-close-loading="backofficeLoading.runDayClose" @run-night-audit="runNightAudit" @run-day-close="runDayCloseAction" />

        <CreditPanel
          v-if="showOpsDomain && canCredit"
          :credit-form="creditForm"
          :credit-lookup-username="creditLookupUsername"
          :credit-profile="creditProfile"
          :mask-sensitive-text="maskSensitiveText"
          :calculate-loading="backofficeLoading.calculateCredit"
          :load-profile-loading="backofficeLoading.loadCreditProfile"
          @calculate-credit="calculateCreditScore"
          @load-profile="loadCreditProfile"
          @update:creditLookupUsername="(v) => (creditLookupUsername.value = v)"
        />

        <ReleasesAuditPanel
          v-if="showGovernanceDomain"
          :releases="releases"
          :audit-logs="auditLogs"
          :user-role="session.user.role"
          :format-date="formatDate"
          @approve-release="approveRelease"
          @rollback-release="rollbackRelease"
        />
      </section>

      <p v-if="messages.success" class="message success">{{ messages.success }}</p>
      <p v-if="messages.error" class="message error">{{ messages.error }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, toRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createApiClient } from './api/client'
import AppHeader from './components/AppHeader.vue'
import ComplaintPanel from './components/ComplaintPanel.vue'
import ContentReleasePanel from './components/ContentReleasePanel.vue'
import CreditPanel from './components/CreditPanel.vue'
import ExportBundlePanel from './components/ExportBundlePanel.vue'
import FinanceClosePanel from './components/FinanceClosePanel.vue'
import FolioOperationsPanel from './components/FolioOperationsPanel.vue'
import GmAnalyticsPanel from './components/GmAnalyticsPanel.vue'
import GovernanceOpsPanel from './components/GovernanceOpsPanel.vue'
import LiveDataPanel from './components/LiveDataPanel.vue'
import LoginPanel from './components/LoginPanel.vue'
import OrderComposer from './components/OrderComposer.vue'
import OrderOperationsPanel from './components/OrderOperationsPanel.vue'
import QuoteReconfirmPanel from './components/QuoteReconfirmPanel.vue'
import RatingsPanel from './components/RatingsPanel.vue'
import ReleasesAuditPanel from './components/ReleasesAuditPanel.vue'
import ServiceDurationPanel from './components/ServiceDurationPanel.vue'
import StatsGrid from './components/StatsGrid.vue'
import { useBackofficeActions } from './composables/useBackofficeActions'
import { useComplaintFlow } from './composables/useComplaintFlow'
import { useContentAndExportFlow } from './composables/useContentAndExportFlow'
import { useDashboardData } from './composables/useDashboardData'
import { useDisplayUtils } from './composables/useDisplayUtils'
import { useFolioOps } from './composables/useFolioOps'
import { useOrderOps } from './composables/useOrderOps'
import { useOrderQuoteFlow } from './composables/useOrderQuoteFlow'
import { useRoleAccess } from './composables/useRoleAccess'
import { useSessionLifecycle } from './composables/useSessionLifecycle'

const props = defineProps({
  viewScope: { type: String, default: 'workspace' },
})

const API_BASE = import.meta.env.VITE_API_BASE || ''
const router = useRouter()

const session = reactive({ user: null, overview: null })
const loading = reactive({ auth: false, dashboard: false, order: false, complaint: false, release: false, exportBundle: false, serviceDuration: false, gmDashboard: false })
const actionLoading = reactive({
  folioCharge: false,
  folioPayment: false,
  folioReversal: false,
  folioSplit: false,
  folioMerge: false,
  folioReceipt: false,
  folioInvoice: false,
  folioPrint: false,
  folioPrintInvoice: false,
  orderTransition: false,
  orderSplit: false,
  orderMerge: false,
})
const messages = reactive({ success: '', error: '' })

const folioPaymentForm = reactive({ amount: '25.00', payment_method: 'cash', note: 'Desk payment' })
const folioChargeForm = reactive({ amount: '18.00', reason: 'Manual minibar charge', payment_method: 'direct_bill' })
const folioReversalForm = reactive({ amount: '10.00', reason: 'Charge posted in error' })
const folioSplitForm = reactive({ allocations: '20.00,30.00' })
const folioMergeForm = reactive({ primary_folio_id: '', secondary_folio_id: '' })
const orderOpsForm = reactive({
  next_state: 'confirmed',
  reversal_reason: '',
  split_allocations: 'KitchenA|WH1|gold|1;KitchenB|WH2|silver|1',
  merge_supplier: 'KitchenUnified',
  merge_warehouse: 'WH-Central',
  merge_sla_tier: 'standard',
})

const receiptPreview = ref(null)
const invoicePreview = ref(null)
const printJob = ref(null)
const viewScopeRef = toRef(props, 'viewScope')

const api = createApiClient({ baseUrl: API_BASE, getToken: () => '' })

function clearMessages() {
  messages.success = ''
  messages.error = ''
}

const {
  folios,
  orders,
  ratings,
  releases,
  auditLogs,
  lineageRows,
  serviceDurationMetrics,
  gmDashboardMetrics,
  selectedFolio,
  selectedOrder,
  refreshDashboard,
  loadServiceDurations,
  loadGmDashboard,
  resetDashboardData,
} = useDashboardData({
  api,
  session,
  loading,
  messages,
  clearMessages,
  onAuthFailure: (error) => {
    logout(false)
    messages.error = error.message
  },
  ratingForm: reactive({ order_id: '' }),
})

const access = useRoleAccess(session, viewScopeRef)
const {
  canCreateOrder,
  canFileComplaint,
  canManageContent,
  canExport,
  canManageFolios,
  canOperateOrders,
  canRate,
  canGovernance,
  canRunClose,
  canCredit,
  canSeeServiceDurations,
  canSeeGmDashboard,
  canViewSensitiveNotes,
  isWorkspaceScope,
  showOpsDomain,
  showGovernanceDomain,
} = access

const { readableRole, formatDate, maskReceiptLine, maskSensitiveText } = useDisplayUtils(canViewSensitiveNotes)

const {
  releaseForm,
  exportForm,
  latestExport,
  createRelease,
  approveRelease,
  rollbackRelease,
  createExportBundle,
  resetContentAndExportState,
} = useContentAndExportFlow({ api, refreshDashboard, clearMessages, messages, loading })

const {
  ratingForm,
  datasetForm,
  lineageForm,
  closeForm,
  nightAuditForm,
  creditForm,
  creditLookupUsername,
  nightAuditResult,
  dayCloseResult,
  creditProfile,
  backofficeLoading,
  submitRating,
  createDataset,
  createLineage,
  runNightAudit,
  runDayCloseAction,
  calculateCreditScore,
  loadCreditProfile,
  resetBackofficeState,
} = useBackofficeActions({ api, clearMessages, messages, ratings, lineageRows })

const {
  complaintPacket,
  lastComplaintId,
  complaintForm,
  complaintEligibility,
  createComplaint,
  exportComplaintPacket,
  resetComplaintState,
} = useComplaintFlow({ api, selectedFolio, orders, refreshDashboard, clearMessages, messages, loading })

  const {
    pendingQuote,
    quoteExpiryDisplay,
    quoteExpired,
    createOrder,
  clearPendingQuote,
  submitConfirmedOrder,
  resetOrderQuoteState,
} = useOrderQuoteFlow({ api, selectedFolio, refreshDashboard, clearMessages, messages, loading })

function selectFolio(folio) {
  selectedFolio.value = folio
}

function selectOrder(order) {
  selectedOrder.value = order
  ratingForm.order_id = order.id
}

const {
  postFolioPayment,
  postFolioCharge,
  postFolioReversal,
  splitFolioBill,
  mergeFoliosBill,
  loadFolioReceipt,
  loadFolioInvoice,
  queueFolioPrint,
  queueFolioInvoicePrint,
} = useFolioOps({
  api,
  actionLoading,
  selectedFolio,
  folioChargeForm,
  folioPaymentForm,
  folioReversalForm,
  folioSplitForm,
  folioMergeForm,
  receiptPreview,
  invoicePreview,
  printJob,
  clearMessages,
  messages,
  refreshDashboard,
})

const { transitionOrderState, splitOrderDims, mergeOrderDims } = useOrderOps({
  api,
  actionLoading,
  selectedOrder,
  orderOpsForm,
  clearMessages,
  messages,
  refreshDashboard,
})

function resetSessionState() {
  resetDashboardData()
  receiptPreview.value = null
  invoicePreview.value = null
  printJob.value = null
  resetOrderQuoteState()
  resetComplaintState()
  resetContentAndExportState()
  resetBackofficeState()
}

const { login, logout, lockoutSeconds, idleWarningSeconds, onMountedSession, onBeforeUnmountSession } = useSessionLifecycle({
  session,
  loading,
  messages,
  api,
  router,
  clearMessages,
  onRefreshDashboard: refreshDashboard,
  onResetState: resetSessionState,
})

const stats = computed(() => {
  if (!session.overview) {
    return []
  }
  return [
    { label: 'Open folios', value: session.overview.open_folios, note: 'org-scoped access' },
    { label: 'Active orders', value: session.overview.active_orders, note: 'tax reconfirm tracked' },
    { label: 'Pending content', value: session.overview.pending_content, note: 'approval workflow' },
    { label: 'Open complaints', value: session.overview.open_complaints, note: 'packet export ready' },
    { label: 'Unread releases', value: session.overview.unread_releases, note: 'role-targeted notices' },
    { label: 'Pending exports', value: session.overview.pending_exports, note: 'checksum bundles' },
  ]
})

watch(
  () => selectedOrder.value?.id || '',
  (orderId) => {
    ratingForm.order_id = orderId
  },
  { immediate: true }
)

onMounted(() => {
  onMountedSession()
})

onBeforeUnmount(() => {
  onBeforeUnmountSession()
})
</script>
