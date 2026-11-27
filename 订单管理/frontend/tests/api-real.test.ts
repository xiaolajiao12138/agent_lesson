import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AxiosError, AxiosHeaders, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios';
import { api } from '../src/api';
import { http } from '../src/utils/http/axios';
import { removeLegacyPreviewData } from '../src/utils/token';

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return { get length() { return data.size; }, getItem: key => data.get(key) ?? null,
    setItem: (key, value) => { data.set(key, value); }, removeItem: key => { data.delete(key); },
    clear: () => data.clear(), key: index => [...data.keys()][index] ?? null };
}
const originalAdapter = http.getAxios().defaults.adapter;
let storage: Storage;
beforeEach(() => { storage = memoryStorage(); vi.stubGlobal('localStorage', storage); storage.setItem('order-management:access-token', 'server-issued-token'); });
afterEach(() => { http.getAxios().defaults.adapter = originalAdapter; vi.unstubAllGlobals(); });
const reply = (config: InternalAxiosRequestConfig, data: unknown) => ({ config, data: { code: 200, message: 'ok', data }, status: 200, statusText: 'OK', headers: new AxiosHeaders() });

describe('业务请求统一发送给真实后端', () => {
  it('订单列表走 Axios，并保留查询参数和登录 Token', async () => {
    const received: InternalAxiosRequestConfig[] = [];
    const adapter: AxiosAdapter = async config => { received.push(config); return reply(config, { items: [], total: 0, page: 1, page_size: 8 }); };
    http.getAxios().defaults.adapter = adapter;
    const result = await api.orders({ q: 'order-number', page: 1, page_size: 8 });
    expect(received).toHaveLength(1);
    expect(received[0]?.url).toBe('/orders');
    expect(received[0]?.headers.get('Authorization')).toBe('Bearer server-issued-token');
    expect(received[0]?.params.q).toBe('order-number');
    expect(result.items).toEqual([]);
  });
  it('登录结果由后端返回，登录请求不携带旧 Token', async () => {
    const received: InternalAxiosRequestConfig[] = [];
    http.getAxios().defaults.adapter = async config => { received.push(config); return reply(config, { access_token: 'new-server-token', token_type: 'bearer', user: { id: 'server-user', username: 'backend-account', name: '后端用户', role: 'customer', tenant_id: 'server-tenant' } }); };
    const result = await api.login({ username: 'backend-account', password: 'test-only-password' });
    expect(result.access_token).toBe('new-server-token');
    expect(received[0]?.url).toBe('/auth/login');
    expect(received[0]?.headers.has('Authorization')).toBe(false);
  });
  it('问答接口不可用时直接报错，不返回固定回答', async () => {
    http.getAxios().defaults.adapter = async config => {
      throw new AxiosError('Service Unavailable', 'ERR_BAD_RESPONSE', config, undefined,
        { config, status: 503, statusText: 'Unavailable', headers: new AxiosHeaders(), data: { code: 503, message: '后端问答接口暂不可用', data: null } });
    };
    await expect(api.answer({ message: '查询订单', history: [] })).rejects.toThrow('后端问答接口暂不可用');
  });
  it('转人工通过 HTTP 发送幂等键和问题，而不是在浏览器生成工单', async () => {
    const received: InternalAxiosRequestConfig[] = [];
    http.getAxios().defaults.adapter = async config => { received.push(config); return reply(config, { id: 'ticket-from-server' }); };
    const result = await api.transfer({ question: '需要人工协助', order_id: null }, 'request-id-001');
    expect(result.id).toBe('ticket-from-server');
    expect(received[0]?.url).toBe('/tickets');
    expect(received[0]?.headers.get('Idempotency-Key')).toBe('request-id-001');
  });
});

describe('只清理本项目旧的界面体验数据', () => {
  it('删除旧数据、聊天和体验登录，保留其他应用的浏览器数据', () => {
    storage.setItem('order-management:demo:v1', '{"orders":[]}');
    storage.setItem('order-management:chat:u-customer', 'old preview messages');
    storage.setItem('order-management:access-token', 'demo:u-customer');
    storage.setItem('order-management:user', '{"id":"u-customer"}');
    storage.setItem('other-app:token', 'keep');
    removeLegacyPreviewData(storage);
    expect(storage.getItem('order-management:demo:v1')).toBeNull();
    expect(storage.getItem('order-management:chat:u-customer')).toBeNull();
    expect(storage.getItem('order-management:access-token')).toBeNull();
    expect(storage.getItem('order-management:user')).toBeNull();
    expect(storage.getItem('other-app:token')).toBe('keep');
  });
  it('已有真实登录 Token 和身份不能被清理', () => {
    storage.setItem('order-management:user', '{"id":"server-user"}');
    storage.setItem('order-management:demo:v1', 'old data');
    removeLegacyPreviewData(storage);
    expect(storage.getItem('order-management:access-token')).toBe('server-issued-token');
    expect(storage.getItem('order-management:user')).toBe('{"id":"server-user"}');
    expect(storage.getItem('order-management:demo:v1')).toBeNull();
  });
});
