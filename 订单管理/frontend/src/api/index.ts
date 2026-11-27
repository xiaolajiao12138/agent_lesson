/** 页面只通过 Axios 请求真实后端。业务接口由你在 Python 中实现。
 * 成功响应约定：{ code: 200, message: string, data: T }。
 */
import { http } from '../utils/http/axios';
import type { ChatAnswer, ChatInput, ListParams, LoginInput, LoginResult, Order, Page, ReviewInput, Ticket, TransferInput, User } from '../types';
const idPath = (id: string) => encodeURIComponent(id);

export const api = {
  login: (data: LoginInput): Promise<LoginResult> => http.post<LoginResult>(
    { url: '/auth/login', data }, { withToken: false },
  ),
  me: (): Promise<User> => http.get<User>({ url: '/auth/me' }),
  orders: (params: ListParams = {}): Promise<Page<Order>> => http.get<Page<Order>>({ url: '/orders', params }),
  order: (id: string): Promise<Order> => http.get<Order>({ url: `/orders/${idPath(id)}` }),
  answer: (data: ChatInput): Promise<ChatAnswer> => http.post<ChatAnswer>({ url: '/agent/answer', data, timeout: 90000 }),
  transfer: (data: TransferInput, key: string): Promise<Ticket> => http.post<Ticket>({
    url: '/tickets', data, headers: { 'Idempotency-Key': key },
  }),
  ticket: (id: string): Promise<Ticket> => http.get<Ticket>({ url: `/tickets/${idPath(id)}` }),
  approvals: (params: ListParams = {}): Promise<Page<Ticket>> => http.get<Page<Ticket>>({ url: '/approvals', params }),
  review: (id: string, data: ReviewInput): Promise<Ticket> => http.post<Ticket>({ url: `/tickets/${idPath(id)}/review`, data }),
};
