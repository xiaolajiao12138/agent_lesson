import { reactive } from 'vue';
export const notice = reactive({ text: '', kind: 'success' as 'success' | 'error' });
let timer: ReturnType<typeof setTimeout>;
export function notify(text: string, kind: 'success' | 'error' = 'success') {
  notice.text = text; notice.kind = kind; clearTimeout(timer);
  timer = setTimeout(() => { notice.text = ''; }, 4500);
}
export function showError(error: unknown) { notify(error instanceof Error ? error.message : '操作失败，请重试', 'error'); }
