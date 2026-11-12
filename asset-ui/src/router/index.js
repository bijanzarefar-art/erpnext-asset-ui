import { createRouter, createWebHistory } from 'vue-router'
import { session, loadSession } from '@/api/session'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: { name: 'Dashboard' } },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { needs: 'asset_list' } },
      { path: 'asset/new', name: 'AssetNew', component: () => import('@/views/AssetNew.vue'), meta: { needs: 'asset_create' } },
      { path: 'asset-list', name: 'Assets', component: () => import('@/views/AssetList.vue'), meta: { needs: 'asset_list' } },
      { path: 'movement/new', name: 'MovementNew', component: () => import('@/views/MovementForm.vue'), meta: { needs: 'asset_movement' } },
      { path: 'asset/:name', name: 'Asset', component: () => import('@/views/AssetDetail.vue'), props: true },
      { path: 'no-access', name: 'NoAccess', component: () => import('@/views/NoAccess.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to) => {
  if (!session.ready) await loadSession()
  if (!to.meta.public && !session.user) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'Login' && session.user) return { name: 'Dashboard' }
  // Block routes the caller has no permission for. The server enforces this too;
  // this only avoids showing a form that would fail on submit.
  if (to.meta.needs && !session.features[to.meta.needs]) {
    return { name: 'NoAccess', query: { from: to.fullPath } }
  }
})

export default router
