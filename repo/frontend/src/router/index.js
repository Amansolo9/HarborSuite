import { createRouter, createWebHistory } from 'vue-router'

import FinanceView from '../views/FinanceView.vue'
import GovernanceView from '../views/GovernanceView.vue'
import LoginView from '../views/LoginView.vue'
import WorkspaceView from '../views/WorkspaceView.vue'

const routes = [
  { path: '/', redirect: '/workspace' },
  { path: '/login', component: LoginView, meta: { publicOnly: true } },
  {
    path: '/workspace',
    component: WorkspaceView,
    meta: {
      requiresAuth: true,
      roles: ['guest', 'front_desk', 'service_staff', 'finance', 'content_editor', 'general_manager'],
    },
  },
  {
    path: '/workspace/finance',
    component: FinanceView,
    meta: { requiresAuth: true, roles: ['finance', 'general_manager'] },
  },
  {
    path: '/workspace/governance',
    component: GovernanceView,
    meta: { requiresAuth: true, roles: ['finance', 'general_manager', 'content_editor'] },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export function resolveNavigation(to) {
  const apiBase = import.meta.env.VITE_API_BASE || ''

  const readSession = () =>
    fetch(`${apiBase}/api/v1/auth/me`, {
      credentials: 'include',
    })

  if (to.meta.publicOnly) {
    return readSession()
      .then((response) => (response.ok ? '/workspace' : true))
      .catch(() => true)
  }

  if (to.meta.requiresAuth) {
    return readSession()
      .then((response) => {
        if (!response.ok) {
          return '/login'
        }
        return response.json().then((payload) => {
          const serverRole = payload.role
          if (to.meta.roles && !to.meta.roles.includes(serverRole)) {
            return '/workspace'
          }
          return true
        })
      })
      .catch(() => '/login')
  }

  return true
}

router.beforeEach((to) => resolveNavigation(to))

export default router
