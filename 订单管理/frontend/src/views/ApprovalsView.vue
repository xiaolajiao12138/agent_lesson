<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../api';
import type { Order, Ticket } from '../types';
import { dateTime, eventLabels, money } from '../utils/format';
import { notify, showError } from '../stores/notice';
import Icon from '../components/Icon.vue';
import StatusBadge from '../components/StatusBadge.vue';
import Modal from '../components/Modal.vue';
const tickets = ref<Ticket[]>([]), total = ref(0), page = ref(1), selected = ref<Ticket | null>(null), order = ref<Order | null>(null);
const status = ref('pending_review'), q = ref(''), loading = ref(false), errorText = ref('');
const decision = ref<'approved' | 'rejected' | null>(null), note = ref(''), reviewing = ref(false);
// 确认框固定操作目标，不能随迟到的列表刷新改变。
const reviewTarget = ref<{ id: string; version: number; code: string } | null>(null);
const tabs = [ { label: '待审批', value: 'pending_review' }, { label: '已通过', value: 'approved' }, { label: '已拒绝', value: 'rejected' }, { label: '全部申请', value: '' } ];
let selectionGeneration = 0, loadGeneration = 0;
async function selectTicket(ticket: Ticket) {
  const generation = ++selectionGeneration; selected.value = ticket; order.value = null;
  if (ticket.order_id) { try { const data = await api.order(ticket.order_id); if (generation === selectionGeneration) order.value = data; } catch (error) { if (generation === selectionGeneration) showError(error); } }
}
async function load(nextPage = 1) {
  const generation = ++loadGeneration; loading.value = true; errorText.value = '';
  try {
    const data = await api.approvals({ status: status.value, q: q.value, page: nextPage, page_size: 6 });
    if (generation !== loadGeneration) return;
    tickets.value = data.items; total.value = data.total; page.value = data.page;
    if (data.items.length) await selectTicket(data.items.find(item => item.id === selected.value?.id) || data.items[0]!);
    else { ++selectionGeneration; selected.value = null; order.value = null; }
  } catch (error) { if (generation === loadGeneration) errorText.value = error instanceof Error ? error.message : '加载失败'; }
  finally { if (generation === loadGeneration) loading.value = false; }
}
function openReview(value: 'approved' | 'rejected') {
  if (!selected.value) return;
  reviewTarget.value = { id: selected.value.id, version: selected.value.version, code: selected.value.code };
  decision.value = value; note.value = '';
}
async function review() {
  if (!reviewTarget.value || !decision.value || reviewing.value) return;
  const target = reviewTarget.value;
  reviewing.value = true;
  try {
    await api.review(target.id, { decision: decision.value, note: note.value.trim(), version: target.version });
    notify(decision.value === 'approved' ? '申请已通过，处理意见已记录' : '申请已拒绝，处理意见已记录');
    decision.value = null; await load(page.value);
  } catch (error) { showError(error); } finally { reviewing.value = false; }
}
onMounted(() => load());
</script>
<template><div class="page-heading"><div><div class="eyebrow">SERVICE APPROVALS</div><h1>审批中心</h1><p>集中处理客户的人工服务申请，记录每一次审核与反馈。</p></div><button class="button secondary" :disabled="loading" @click="load(page)"><Icon name="refresh" :size="17" />刷新申请</button></div><section class="approval-workspace"><div class="approval-list"><div class="approval-tabs"><button v-for="tab in tabs" :key="tab.value" :class="{ active: status === tab.value }" @click="status = tab.value; load()">{{ tab.label }}</button></div><form class="approval-search" @submit.prevent="load()"><div class="search-field"><Icon name="search" :size="17" /><input v-model="q" aria-label="搜索审批申请" placeholder="搜索申请号、客户或问题" /></div><button type="submit" class="icon-button" aria-label="查询申请"><Icon name="search" :size="18" /></button></form><div class="list-caption"><span>{{ loading ? '正在加载…' : `共 ${total} 条服务申请` }}</span><span>最新提交优先</span></div><div v-if="errorText" class="empty-state"><h3>加载失败</h3><p>{{ errorText }}</p><button class="button secondary" @click="load()">重试</button></div><div v-else class="approval-cards"><button v-for="ticket in tickets" :key="ticket.id" class="approval-item" :class="{ selected: selected?.id === ticket.id }" @click="selectTicket(ticket)"><div class="approval-item-top"><strong>{{ ticket.code }}</strong><StatusBadge :status="ticket.status" /></div><p>{{ ticket.question }}</p><div class="approval-item-bottom"><span><span class="tiny-avatar">{{ ticket.customer_name.slice(0, 1) }}</span>{{ ticket.customer_name }}</span><small>{{ dateTime(ticket.created_at) }}</small></div></button><div v-if="!tickets.length && !loading" class="empty-state"><Icon name="clipboard" :size="36" /><h3>暂无此类申请</h3><p>客户转人工后，申请会出现在这里。</p></div></div><div class="approval-pagination"><button class="button text" :disabled="page <= 1 || loading" @click="load(page - 1)">上一页</button><span>{{ page }} / {{ Math.max(1, Math.ceil(total / 6)) }}</span><button class="button text" :disabled="page * 6 >= total || loading" @click="load(page + 1)">下一页</button></div></div><article v-if="selected" class="approval-detail"><header class="approval-detail-header"><div><span class="eyebrow">APPLICATION DETAILS</span><h2>服务申请详情</h2><p>{{ selected.code }}</p></div><StatusBadge :status="selected.status" /></header><div class="approval-detail-content"><div class="applicant-info"><span class="avatar">{{ selected.customer_name.slice(0, 1) }}</span><div><strong>{{ selected.customer_name }}</strong><small>提交于 {{ dateTime(selected.created_at) }}</small></div></div><section class="detail-section"><h3><Icon name="chat" :size="18" />客户问题</h3><div class="question-block">{{ selected.question }}</div></section><section class="detail-section"><h3><Icon name="box" :size="18" />关联订单</h3><div v-if="order" class="linked-order"><div><strong>{{ order.order_no }}</strong><small>{{ order.items[0]?.name }}</small></div><div class="linked-order-right"><strong>{{ money(order.total_cents) }}</strong><StatusBadge :status="order.status" /></div></div><p v-else class="muted">{{ selected.order_id ? '正在读取关联订单…' : '此申请未关联具体订单' }}</p></section><section class="detail-section"><h3><Icon name="clock" :size="18" />处理记录</h3><ol class="timeline"><li v-for="(event, index) in selected.events" :key="index"><span class="timeline-dot" :class="{ done: event.action !== 'created' }"></span><div class="timeline-heading"><strong>{{ eventLabels[event.action] || event.action }}</strong><small>{{ dateTime(event.created_at) }}</small></div><p>{{ event.actor }} · {{ event.note }}</p></li></ol></section></div><footer class="approval-actions"><span><Icon name="shield" :size="15" />审核意见会同步给申请人</span><div v-if="selected.status === 'pending_review'"><button class="button danger-light" @click="openReview('rejected')">拒绝申请</button><button class="button primary" @click="openReview('approved')"><Icon name="check" :size="17" />通过申请</button></div><span v-else class="processed-label"><Icon name="check" :size="16" />该申请已处理</span></footer></article><div v-else class="approval-detail approval-placeholder"><div class="welcome-symbol"><Icon name="clipboard" :size="30" /></div><h2>选择一条申请</h2><p>查看问题详情、关联订单和处理记录。</p></div></section><Modal v-if="decision" :title="decision === 'approved' ? '确认通过申请' : '确认拒绝申请'" @close="!reviewing && (decision = null)"><form class="stack-form" @submit.prevent="review"><p class="form-hint">{{ decision === 'approved' ? '通过后，客户可以查看你的处理意见。此操作仅记录审核结果，不会执行退款或扣款。' : '请说明拒绝原因，帮助客户了解审核结果。' }}</p><p class="form-hint">本次处理：{{ reviewTarget?.code }}</p><label for="review-note">处理意见 <span class="muted">{{ decision === 'approved' ? '（可选）' : '（必填）' }}</span></label><textarea id="review-note" v-model="note" :required="decision === 'rejected'" maxlength="1000" rows="5" placeholder="填写清晰的处理意见，供客户查看"></textarea><div class="modal-actions"><button class="button secondary" type="button" :disabled="reviewing" @click="decision = null">取消</button><button class="button" :class="decision === 'approved' ? 'primary' : 'danger'" :disabled="reviewing || (decision === 'rejected' && !note.trim())" type="submit">{{ reviewing ? '正在提交…' : decision === 'approved' ? '确认通过' : '确认拒绝' }}</button></div></form></Modal></template>
