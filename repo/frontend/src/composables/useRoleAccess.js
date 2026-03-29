import { computed } from 'vue'

export function useRoleAccess(session, viewScope) {
  const role = computed(() => session.user?.role || '')

  const canCreateOrder = computed(() => ['guest', 'front_desk'].includes(role.value))
  const canFileComplaint = computed(() => ['guest', 'service_staff'].includes(role.value))
  const canManageContent = computed(() => role.value === 'content_editor')
  const canExport = computed(() => ['finance', 'general_manager'].includes(role.value))
  const canManageFolios = computed(() => ['front_desk', 'finance'].includes(role.value))
  const canOperateOrders = computed(() => ['front_desk', 'service_staff', 'finance'].includes(role.value))
  const canRate = computed(() => ['guest', 'service_staff'].includes(role.value))
  const canGovernance = computed(() => ['finance', 'general_manager'].includes(role.value))
  const canRunClose = computed(() => ['finance', 'general_manager'].includes(role.value))
  const canCredit = computed(() => ['front_desk', 'finance', 'general_manager'].includes(role.value))
  const canSeeServiceDurations = computed(() => ['service_staff', 'finance', 'general_manager'].includes(role.value))
  const canSeeGmDashboard = computed(() => role.value === 'general_manager')
  const canViewSensitiveNotes = computed(() => ['finance', 'general_manager'].includes(role.value))

  const isWorkspaceScope = computed(() => viewScope.value === 'workspace')
  const isFinanceScope = computed(() => viewScope.value === 'finance')
  const isGovernanceScope = computed(() => viewScope.value === 'governance')
  const showOpsDomain = computed(() => isWorkspaceScope.value || isFinanceScope.value)
  const showGovernanceDomain = computed(() => isWorkspaceScope.value || isGovernanceScope.value)

  return {
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
  }
}
