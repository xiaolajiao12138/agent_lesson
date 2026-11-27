/** 角色用于页面导航。真实数据权限必须由你编写的 Python 后端再次校验。 */
import { reactive } from 'vue';
import { api } from '../api';
import { clearToken, getToken, setToken, removeLegacyPreviewData } from '../utils/token';
import type { LoginInput, User } from '../types';
// 在读取缓存身份之前，移除旧版体验登录和历史数据。
try { removeLegacyPreviewData(localStorage); } catch { /* 浏览器不允许访问存储。 */ }
const key = 'order-management:user';
let initial: User | null = null;
try { initial = JSON.parse(localStorage.getItem(key) || 'null'); } catch { /* 无缓存 */ }
export const auth = reactive({ user: initial, validated: false });
export async function login(input: LoginInput) {
  const result = await api.login(input);
  setToken(result.access_token); auth.user = result.user; auth.validated = true;
  localStorage.setItem(key, JSON.stringify(result.user));
  return result.user;
}
export async function ensureProfile() {
  if (!getToken()) { logout(); return; }
  if (!auth.validated || !auth.user) {
    auth.user = await api.me(); auth.validated = true;
    localStorage.setItem(key, JSON.stringify(auth.user));
  }
}
export function logout() { clearToken(); auth.user = null; auth.validated = false; localStorage.removeItem(key); }
