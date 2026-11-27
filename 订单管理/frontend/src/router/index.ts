import { createRouter, createWebHistory } from 'vue-router';
import { auth, ensureProfile, logout } from '../stores/auth';
import { getToken } from '../utils/token';
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
    { path: '/', component: () => import('../layouts/AppLayout.vue'), children: [
      { path: '', redirect: '/chat' },
      { path: 'chat', name: 'chat', component: () => import('../views/ChatView.vue'), meta: { title: '智能客服', roles: ['customer', 'admin'] } },
      { path: 'orders', name: 'orders', component: () => import('../views/OrdersView.vue'), meta: { title: '订单查询', roles: ['admin'] } },
      { path: 'approvals', name: 'approvals', component: () => import('../views/ApprovalsView.vue'), meta: { title: '审批中心', roles: ['admin'] } },
    ] },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
});
router.beforeEach(async to => {
  if (to.meta.public) return true;
  if (!getToken()) return { name: 'login' };
  try { await ensureProfile(); } catch { logout(); return { name: 'login' }; }
  const roles = to.meta.roles as string[] | undefined;
  if (roles && !roles.includes(auth.user?.role || '')) return { name: 'chat' };
  return true;
});
export default router;
