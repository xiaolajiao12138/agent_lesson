import { describe, expect, it } from 'vitest';
import { DemoService } from '../src/services/demo';

const login = (service: DemoService, username = 'customer') => service.login({ username, password: '123456' });

describe('明确标注的前端演示流程，不替代 Python 业务实现', () => {
  it('客户转人工后，管理员审批，客户能读到同一张工单的新状态', () => {
    const service = new DemoService();
    const customer = login(service);
    const orders = service.listOrders(customer.access_token);
    const ticket = service.createTicket(customer.access_token, { question: '申请退货', order_id: orders.items[0].id }, 'key-001');
    expect(ticket.status).toBe('pending_review');
    const admin = login(service, 'admin');
    expect(service.listApprovals(admin.access_token).items.some((item: { id: string }) => item.id === ticket.id)).toBe(true);
    service.reviewTicket(admin.access_token, ticket.id, { decision: 'approved', note: '同意处理', version: ticket.version });
    const result = service.getTicket(customer.access_token, ticket.id);
    expect(result.status).toBe('approved');
    expect(result.events.at(-1)?.action).toBe('approved');
  });
  it('重复转人工不会重复建单，同 Key 不同问题会报冲突', () => {
    const service = new DemoService();
    const { access_token: token } = login(service);
    const input = { question: '需要人工客服', order_id: null };
    const first = service.createTicket(token, input, 'key-002');
    expect(service.createTicket(token, input, 'key-002').id).toBe(first.id);
    expect(() => service.createTicket(token, { ...input, question: '另一个问题' }, 'key-002')).toThrow(/冲突/);
  });
  it('客户之间订单隔离，客户不能进入审批操作', () => {
    const service = new DemoService();
    const first = login(service);
    const second = login(service, 'customer2');
    const ids = service.listOrders(first.access_token).items.map((item: { id: string }) => item.id);
    expect(service.listOrders(second.access_token).items.every((item: { id: string }) => !ids.includes(item.id))).toBe(true);
    expect(() => service.listApprovals(first.access_token)).toThrow(/管理员/);
  });
  it('已经处理的审批不能被另一个相反意见覆盖', () => {
    const service = new DemoService();
    const customer = login(service);
    const ticket = service.createTicket(customer.access_token, { question: '退货', order_id: null }, 'key-003');
    const admin = login(service, 'admin');
    service.reviewTicket(admin.access_token, ticket.id, { decision: 'approved', note: '', version: ticket.version });
    expect(() => service.reviewTicket(admin.access_token, ticket.id, { decision: 'rejected', note: '拒绝', version: ticket.version })).toThrow(/处理|版本/);
  });
});
