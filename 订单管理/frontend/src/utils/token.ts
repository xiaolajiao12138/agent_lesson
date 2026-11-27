/** 仅保存应用登录 Token。大模型 API Key 绝不能放在这里或任何 VITE_ 变量中。 */
const key = 'order-management:access-token';
export function getToken(): string { return typeof localStorage === 'undefined' ? '' : localStorage.getItem(key) || ''; }
export function setToken(token: string): void { localStorage.setItem(key, token); }
export function clearToken(): void { if (typeof localStorage !== 'undefined') localStorage.removeItem(key); }
