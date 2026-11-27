import type { OrderStatus, ReviewStatus } from '../types';
export const money = (cents: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(cents / 100);
export const dateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value));
export const orderLabels: Record<OrderStatus, string> = { pending_payment: '待付款', paid: '待发货', shipped: '已发货', completed: '已完成', cancelled: '已取消' };
export const reviewLabels: Record<ReviewStatus, string> = { pending_review: '待审批', approved: '已通过', rejected: '已拒绝' };
export const eventLabels: Record<string, string> = { created: '提交申请', approved: '审批通过', rejected: '审批拒绝' };
