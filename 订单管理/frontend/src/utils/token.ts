/** 仅保存应用登录 Token。大模型 API Key 绝不能放在这里或任何 VITE_ 变量中。 */
const key = 'order-management:access-token';
export function getToken(): string { return typeof localStorage === 'undefined' ? '' : localStorage.getItem(key) || ''; }
export function setToken(token: string): void { localStorage.setItem(key, token); }
export function clearToken(): void { if (typeof localStorage !== 'undefined') localStorage.removeItem(key); }

/** 一次性迁移：只移除旧版体验数据，保留真实 Token 和其他应用的数据。 */
export function removeLegacyPreviewData(storage: Storage): void {
  try {
    const versionKey = 'order-management:cache-version';
    if (storage.getItem(versionKey) === '2') return;
    const obsoleteKeys = Array.from({ length: storage.length }, (_, index) => storage.key(index))
      .filter((item): item is string => item !== null && (
        item === 'order-management:demo:v1' || item.startsWith('order-management:chat:')
      ));
    for (const item of obsoleteKeys) storage.removeItem(item);
    if (storage.getItem(key)?.startsWith('demo:')) {
      storage.removeItem(key);
      storage.removeItem('order-management:user');
    }
    storage.setItem(versionKey, '2');
  } catch {
    // 浏览器禁止存储时，清理失败不应阻塞页面启动。
  }
}
