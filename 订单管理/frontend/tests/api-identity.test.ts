import { expect, it, vi } from 'vitest';
import { api } from '../src/api';
it('演示 API 在发起调用时固定身份，不使用延迟期间新登录的账号', async () => {
  const data = new Map<string, string>();
  vi.stubGlobal('localStorage', { getItem: (key: string) => data.get(key) || null, setItem: (key: string, value: string) => data.set(key, value) });
  data.set('order-management:access-token', 'demo:u-customer');
  const pending = api.orders();
  data.set('order-management:access-token', 'demo:u-customer2');
  const result = await pending;
  expect(result.items.every(item => item.customer_id === 'u-customer')).toBe(true);
  vi.unstubAllGlobals();
});
