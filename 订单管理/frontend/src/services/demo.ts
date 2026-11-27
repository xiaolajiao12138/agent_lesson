/** 仅用于前端界面演示，不是 Python 接口，不会调用或冒充真实大模型。
 * 演示数据持久化到本浏览器。关闭 VITE_DEMO_MODE 后，这个适配层不会被 API 调用。
 */
import type { ChatAnswer, ChatInput, ListParams, LoginInput, LoginResult, Order, Page, ReviewInput, Ticket, TransferInput, User } from '../types';

interface DemoState { version: number; orders: Order[]; tickets: Ticket[]; keys: Record<string, { signature: string; id: string }> }
const users: User[] = [
  { id: 'u-customer', username: 'customer', name: '林小满', role: 'customer', tenant_id: 'demo-shop' },
  { id: 'u-admin', username: 'admin', name: '林经理', role: 'admin', tenant_id: 'demo-shop' },
  { id: 'u-customer2', username: 'customer2', name: '周亦安', role: 'customer', tenant_id: 'demo-shop' },
];
const clone = <T>(value: T): T => structuredClone(value);
const uid = () => crypto.randomUUID();
const now = () => new Date().toISOString();
const storageKey = 'order-management:demo:v1';
function seed(): DemoState {
  const catalog = [ ['无线降噪耳机', 'AUDIO-001', 89900], ['桌面智能音箱', 'AUDIO-002', 35900], ['机械键盘', 'KEY-001', 46900], ['便携显示器', 'SCREEN-001', 129900], ['多口充电器', 'POWER-001', 19900], ['人体工学鼠标', 'MOUSE-001', 32900] ] as const;
  const statuses: Order['status'][] = ['shipped', 'paid', 'completed', 'pending_payment', 'completed', 'paid', 'cancelled', 'shipped'];
  const orders: Order[] = statuses.map((status, index) => {
    const product = catalog[index % catalog.length]!;
    const owner = index === 4 || index === 6 ? users[2]! : users[0]!;
    const quantity = index === 1 ? 2 : 1;
    return { id: `order-${index + 1}`, order_no: `ORD202611${String(27 - index).padStart(2, '0')}00${index + 1}`, customer_id: owner.id, customer_name: owner.name, phone: owner.id === 'u-customer' ? '138****6028' : '139****9182', address: '江西省九江市 · 演示收货地址', items: [{ name: product[0], sku: product[1], quantity, price_cents: product[2] }], total_cents: product[2] * quantity, status, created_at: new Date(Date.now() - index * 86400000).toISOString(), tracking_no: status === 'shipped' || status === 'completed' ? `SF-DEMO-000${index + 1}` : null };
  });
  const tickets: Ticket[] = [
    { id: 'ticket-seed-1', code: 'SR20261127001', order_id: orders[0]!.id, customer_id: users[0]!.id, customer_name: users[0]!.name, question: '收到的耳机左侧没有声音，想申请退换货，请帮我核实处理。', status: 'pending_review', version: 1, created_at: now(), events: [{ actor: users[0]!.name, action: 'created', note: '客户提交售后申请', created_at: now() }] },
    { id: 'ticket-seed-2', code: 'SR20261126002', order_id: orders[2]!.id, customer_id: users[0]!.id, customer_name: users[0]!.name, question: '需要补开订单发票，请协助处理。', status: 'approved', version: 2, created_at: new Date(Date.now() - 86400000).toISOString(), events: [{ actor: users[0]!.name, action: 'created', note: '客户提交申请', created_at: new Date(Date.now() - 86400000).toISOString() }, { actor: users[1]!.name, action: 'approved', note: '申请已受理，请等待客服跟进。', created_at: now() }] },
  ];
  return { version: 1, orders, tickets, keys: {} };
}

export class DemoService {
  private state: DemoState;
  constructor(private storage?: Pick<Storage, 'getItem' | 'setItem'>) {
    this.state = seed();
    try {
      const saved = storage?.getItem(storageKey);
      const parsed = saved ? JSON.parse(saved) : null;
      if (parsed?.version === 1 && Array.isArray(parsed.orders) && Array.isArray(parsed.tickets) && parsed.keys) this.state = parsed;
    } catch { /* 损坏的演示数据不影响页面，恢复到初始样例。 */ }
  }
  private save() { try { this.storage?.setItem(storageKey, JSON.stringify(this.state)); } catch { /* 禁用存储时维持本次会话内演示。 */ } }
  private actor(token: string): User {
    const user = users.find(item => token === `demo:${item.id}`);
    if (!user) throw new Error('请先登录演示账号');
    return user;
  }
  private admin(token: string): User { const user = this.actor(token); if (user.role !== 'admin') throw new Error('该操作需要管理员角色'); return user; }
  private page<T>(items: T[], params: ListParams = {}): Page<T> { const page = Math.max(1, params.page || 1), page_size = Math.max(1, params.page_size || 10); return clone({ items: items.slice((page - 1) * page_size, page * page_size), total: items.length, page, page_size }); }
  login(input: LoginInput): LoginResult {
    const user = users.find(item => item.username === input.username.trim());
    if (!user || input.password !== '123456') throw new Error('账号或密码不正确');
    return { access_token: `demo:${user.id}`, token_type: 'bearer', user: clone(user) };
  }
  getMe(token: string): User { return clone(this.actor(token)); }
  listOrders(token: string, params: ListParams = {}): Page<Order> {
    const user = this.actor(token), q = params.q?.trim().toLowerCase() || '';
    const items = this.state.orders.filter(order => (user.role === 'admin' || order.customer_id === user.id) && (!params.status || order.status === params.status) && (!q || `${order.order_no} ${order.customer_name} ${order.items.map(item => item.name).join(' ')}`.toLowerCase().includes(q)));
    return this.page(items, params);
  }
  getOrder(token: string, id: string): Order {
    const user = this.actor(token), order = this.state.orders.find(item => item.id === id && (user.role === 'admin' || item.customer_id === user.id));
    if (!order) throw new Error('订单不存在或无权查看');
    return clone(order);
  }
  answer(token: string, input: ChatInput): ChatAnswer {
    this.actor(token);
    const message = input.message.trim();
    if (!message) throw new Error('请输入问题');
    const order = this.listOrders(token).items[0];
    if (/人工|退货|退款|换货|投诉|发票/.test(message)) return { route: 'transfer', message: '演示回复：这类问题需要人工核实。你可以关联订单并提交客服申请，由管理员在审批页面处理。真实大模型问答接口等待你接入。', order_id: order?.id || null };
    return { route: 'answer', message: `演示回复：你可以咨询订单状态、物流或售后问题。${order ? `最近的订单为 ${order.order_no}。` : ''}页面目前使用浏览器演示数据，真实回答需要你实现问答接口。`, order_id: order?.id || null };
  }
  createTicket(token: string, input: TransferInput, key: string): Ticket {
    const user = this.actor(token), question = input.question.trim();
    if (!question) throw new Error('请填写需要客服处理的问题');
    if (input.order_id) this.getOrder(token, input.order_id);
    const signature = JSON.stringify({ question, order_id: input.order_id }), scopedKey = `${user.id}:${key}`;
    const existing = this.state.keys[scopedKey];
    if (existing) {
      if (existing.signature !== signature) throw new Error('幂等键冲突：本次内容与之前不同');
      return this.getTicket(token, existing.id);
    }
    const ticket: Ticket = { id: uid(), code: `SR${Date.now().toString().slice(-10)}`, order_id: input.order_id, customer_id: user.id, customer_name: user.name, question, status: 'pending_review', version: 1, created_at: now(), events: [{ actor: user.name, action: 'created', note: '客户转人工，等待处理', created_at: now() }] };
    this.state.tickets.unshift(ticket); this.state.keys[scopedKey] = { signature, id: ticket.id }; this.save();
    return clone(ticket);
  }
  getTicket(token: string, id: string): Ticket {
    const user = this.actor(token), ticket = this.state.tickets.find(item => item.id === id && (user.role === 'admin' || item.customer_id === user.id));
    if (!ticket) throw new Error('申请不存在或无权查看');
    return clone(ticket);
  }
  listApprovals(token: string, params: ListParams = {}): Page<Ticket> {
    this.admin(token);
    const q = params.q?.trim() || '';
    return this.page(this.state.tickets.filter(item => (!params.status || item.status === params.status) && (!q || `${item.code} ${item.customer_name} ${item.question}`.includes(q))), params);
  }
  reviewTicket(token: string, id: string, input: ReviewInput): Ticket {
    const user = this.admin(token), ticket = this.state.tickets.find(item => item.id === id);
    if (!ticket) throw new Error('申请不存在');
    if (ticket.status !== 'pending_review' || ticket.version !== input.version) throw new Error('申请已处理或版本变化，请刷新后再操作');
    if (!['approved', 'rejected'].includes(input.decision)) throw new Error('审批决定无效');
    if (input.decision === 'rejected' && !input.note.trim()) throw new Error('请填写拒绝原因');
    ticket.status = input.decision; ticket.version += 1;
    ticket.events.push({ actor: user.name, action: input.decision, note: input.note.trim() || '申请已通过，请由客服继续跟进。', created_at: now() });
    this.save(); return clone(ticket);
  }
}
export const demo = new DemoService(typeof localStorage !== 'undefined' ? localStorage : undefined);
