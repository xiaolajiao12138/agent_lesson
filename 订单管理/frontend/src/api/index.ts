/** 业务接口声明，不是业务实现。默认明确使用前端演示；真实模式只走 Axios。
 * 后端应按照 docs/接口练习约定.md 返回 { code: 200, message, data }。
 */
import { http } from '../utils/http/axios';
import { getToken } from '../utils/token';
import { demo } from '../services/demo';
import type { ChatAnswer, ChatInput, ListParams, LoginInput, LoginResult, Order, Page, ReviewInput, Ticket, TransferInput, User } from '../types';
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== 'false';
const preview = async <T>(action: () => T): Promise<T> => { await new Promise(resolve => setTimeout(resolve, 240)); return action(); };
// 让演示请求与真实 HTTP 请求一样，在发起时就固定本次身份。
const previewAuthed = <T>(action: (token: string) => T): Promise<T> => { const token = getToken(); return preview(() => action(token)); };
const idPath = (id: string) => encodeURIComponent(id);

export const api = {
  login: (data: LoginInput): Promise<LoginResult> => DEMO_MODE ? preview(() => demo.login(data)) : http.post({ url: '/auth/login', data }, { withToken: false }),
  me: (): Promise<User> => DEMO_MODE ? previewAuthed(token => demo.getMe(token)) : http.get({ url: '/auth/me' }),
  orders: (params: ListParams = {}): Promise<Page<Order>> => DEMO_MODE ? previewAuthed(token => demo.listOrders(token, params)) : http.get({ url: '/orders', params }),
  order: (id: string): Promise<Order> => DEMO_MODE ? previewAuthed(token => demo.getOrder(token, id)) : http.get({ url: `/orders/${idPath(id)}` }),
  answer: (data: ChatInput): Promise<ChatAnswer> => DEMO_MODE ? previewAuthed(token => demo.answer(token, data)) : http.post({ url: '/agent/answer', data, timeout: 90000 }),
  transfer: (data: TransferInput, key: string): Promise<Ticket> => DEMO_MODE ? previewAuthed(token => demo.createTicket(token, data, key)) : http.post({ url: '/tickets', data, headers: { 'Idempotency-Key': key } }),
  ticket: (id: string): Promise<Ticket> => DEMO_MODE ? previewAuthed(token => demo.getTicket(token, id)) : http.get({ url: `/tickets/${idPath(id)}` }),
  approvals: (params: ListParams = {}): Promise<Page<Ticket>> => DEMO_MODE ? previewAuthed(token => demo.listApprovals(token, params)) : http.get({ url: '/approvals', params }),
  review: (id: string, data: ReviewInput): Promise<Ticket> => DEMO_MODE ? previewAuthed(token => demo.reviewTicket(token, id, data)) : http.post({ url: `/tickets/${idPath(id)}/review`, data }),
};
