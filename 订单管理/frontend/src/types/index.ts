/** 前后端约定类型。Python 业务接口留给你实现，字段说明见 docs/接口练习约定.md。 */
export type Role = 'customer' | 'admin';
export interface User { id: string; username: string; name: string; role: Role; tenant_id: string }
export interface LoginInput { username: string; password: string }
export interface LoginResult { access_token: string; token_type: string; user: User }
export type OrderStatus = 'pending_payment' | 'paid' | 'shipped' | 'completed' | 'cancelled';
export interface OrderItem { sku: string; name: string; quantity: number; price_cents: number }
export interface Order { id: string; order_no: string; customer_id: string; customer_name: string; phone: string; address: string; items: OrderItem[]; total_cents: number; status: OrderStatus; created_at: string; tracking_no: string | null }
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface ListParams { q?: string; status?: string; page?: number; page_size?: number }
export type ReviewStatus = 'pending_review' | 'approved' | 'rejected';
export interface TicketEvent { actor: string; action: string; note: string; created_at: string }
export interface Ticket { id: string; code: string; order_id: string | null; customer_id: string; customer_name: string; question: string; status: ReviewStatus; version: number; created_at: string; events: TicketEvent[] }
export interface TransferInput { question: string; order_id: string | null }
export interface ReviewInput { decision: 'approved' | 'rejected'; note: string; version: number }
export interface ChatInput { message: string; history: { role: 'user' | 'assistant'; content: string }[] }
export interface ChatAnswer { route: 'answer' | 'transfer'; message: string; order_id?: string | null }
