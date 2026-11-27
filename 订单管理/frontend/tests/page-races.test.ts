import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { computed, reactive, ref } from 'vue';

// 测试真正的 SFC script setup，注入外部 API 和生命周期，重现网络响应先后颠倒。
function loadScript(view: string, expose: string[], overrides: Record<string, unknown>) {
  const source = readFileSync(new URL(`../src/views/${view}.vue`, import.meta.url), 'utf8');
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)![1]!.replace(/^import .*;$/gm, '');
  const text = ts.transpileModule(`${script}\nreturn { ${expose.join(', ')} };`, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None } }).outputText;
  const bindings = { ref, computed, onMounted: () => {}, onUnmounted: () => {}, onBeforeUnmount: () => {}, nextTick: async () => {}, notify: () => {}, showError: () => {}, auth: { user: { id: 'test-customer' } }, ...overrides };
  return new Function(...Object.keys(bindings), text)(...Object.values(bindings));
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
const ticket = (id: string) => ({ id, code: id, question: id, order_id: null, customer_id: 'test-customer', customer_name: '客户', status: 'pending_review', version: 1, events: [], created_at: new Date().toISOString() });

function memoryStorage() { const data = new Map<string, string>(); return { getItem: (key: string) => data.get(key) || null, setItem: (key: string, value: string) => data.set(key, value), removeItem: (key: string) => data.delete(key), data }; }

describe('页面异步请求边界', () => {
  it('打开 A 的审批确认后，迟到列表刷新选中 B 也只能提交 A', async () => {
    const pending = deferred<unknown>();
    const submitted: string[] = [];
    const api = { approvals: () => pending.promise, review: async (id: string) => { submitted.push(id); return ticket(id); } };
    const page = loadScript('ApprovalsView', ['selected', 'openReview', 'load', 'review'], { api });
    page.selected.value = ticket('A');
    const loading = page.load();
    page.openReview('approved');
    pending.resolve({ items: [ticket('B')], total: 1, page: 1, page_size: 6 });
    await loading; await page.review();
    expect(submitted).toEqual(['A']);
  });
  it('新对话忽略前一个会话的迟到模型回复', async () => {
    vi.stubGlobal('localStorage', memoryStorage());
    const pending = deferred<unknown>();
    const page = loadScript('ChatView', ['messages', 'send', 'resetChat', 'busy'], { api: { answer: () => pending.promise } });
    const sending = page.send('旧会话问题');
    page.resetChat();
    pending.resolve({ route: 'answer', message: '旧会话回复' }); await sending;
    expect(page.messages.value).toEqual([]);
    expect(page.busy.value).toBe(false);
    vi.unstubAllGlobals();
  });
  it('切换账号后，旧请求的回复不能写回原页面', async () => {
    const storage = memoryStorage(); vi.stubGlobal('localStorage', storage);
    const pending = deferred<unknown>();
    const auth = reactive({ user: { id: 'alice' } });
    const page = loadScript('ChatView', ['send', 'messages'], { auth, api: { answer: () => pending.promise } });
    const sending = page.send('Alice 的问题');
    auth.user = { id: 'bob' };
    pending.resolve({ route: 'answer', message: 'Alice 的回复' }); await sending;
    expect(page.messages.value.map((item: { role: string }) => item.role)).toEqual(['user']);
    vi.unstubAllGlobals();
  });
  it('较早的订单详情响应不能覆盖较晚选择的订单', async () => {
    const first = deferred<unknown>(), second = deferred<unknown>();
    const page = loadScript('OrdersView', ['selected', 'openDetail'], { api: { order: (id: string) => id === 'A' ? first.promise : second.promise } });
    const a = page.openDetail('A'), b = page.openDetail('B');
    second.resolve({ id: 'B' }); await b; first.resolve({ id: 'A' }); await a;
    expect(page.selected.value.id).toBe('B');
  });
});
