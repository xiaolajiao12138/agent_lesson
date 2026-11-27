<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '../api';
import { auth } from '../stores/auth';
import { notify, showError } from '../stores/notice';
import type { ChatAnswer, Order, Ticket } from '../types';
import Icon from '../components/Icon.vue';
import Modal from '../components/Modal.vue';
import StatusBadge from '../components/StatusBadge.vue';
import { dateTime } from '../utils/format';
interface Message { id: string; role: 'user' | 'assistant'; content: string; route?: ChatAnswer['route']; ticket?: Ticket; order_id?: string | null; question?: string; error?: boolean }
const messages = ref<Message[]>([]), input = ref(''), busy = ref(false), scroller = ref<HTMLElement | null>(null);
const orders = ref<Order[]>([]), showTransfer = ref(false), transferring = ref(false), refreshing = ref('');
const transferQuestion = ref(''), transferOrder = ref(''), transferKey = ref(''), activeMessage = ref<Message | null>(null);
const chatOwnerId = auth.user?.id;
let conversationGeneration = 0, mounted = true;
const isActive = (generation: number) => mounted && generation === conversationGeneration && auth.user?.id === chatOwnerId;
onBeforeUnmount(() => { mounted = false; ++conversationGeneration; });
const suggestions = ['我的订单发货了吗？', '我想申请退换货', '需要人工客服协助'];
async function scrollBottom() { await nextTick(); scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' }); }
onMounted(async () => {
  try { orders.value = (await api.orders({ page_size: 100 })).items; } catch (error) { showError(error); }
  scrollBottom();
});
async function send(value?: string) {
  const question = (value || input.value).trim(); if (!question || busy.value) return;
  const generation = conversationGeneration;
  const history = messages.value.filter(item => !item.error).slice(-10).map(item => ({ role: item.role, content: item.content }));
  messages.value.push({ id: crypto.randomUUID(), role: 'user', content: question }); input.value = ''; busy.value = true; scrollBottom();
  try { const answer = await api.answer({ message: question, history }); if (!isActive(generation)) return; messages.value.push({ id: crypto.randomUUID(), role: 'assistant', content: answer.message, route: answer.route, order_id: answer.order_id, question }); }
  catch (error) { if (!isActive(generation)) return; messages.value.push({ id: crypto.randomUUID(), role: 'assistant', content: error instanceof Error ? error.message : '请求失败，请重试', error: true }); }
  finally { if (isActive(generation)) { busy.value = false; scrollBottom(); } }
}
function openTransfer(message?: Message) {
  activeMessage.value = message || null;
  transferQuestion.value = message?.question || [...messages.value].reverse().find(item => item.role === 'user')?.content || '';
  transferOrder.value = message?.order_id || '';
  transferKey.value = crypto.randomUUID(); showTransfer.value = true;
}
async function transfer() {
  if (transferring.value || !transferQuestion.value.trim()) return;
  transferring.value = true;
  const generation = conversationGeneration, sourceMessage = activeMessage.value;
  try {
    const ticket = await api.transfer({ question: transferQuestion.value.trim(), order_id: transferOrder.value || null }, transferKey.value);
    if (!isActive(generation)) return;
    if (sourceMessage) sourceMessage.ticket = ticket;
    else messages.value.push({ id: crypto.randomUUID(), role: 'assistant', content: '已提交人工服务申请，你可以在下方查看处理进度。', ticket });
    showTransfer.value = false; scrollBottom(); notify('人工服务申请已提交');
  } catch (error) { if (isActive(generation)) showError(error); } finally { if (isActive(generation)) transferring.value = false; }
}
async function refreshTicket(message: Message) {
  if (!message.ticket) return; refreshing.value = message.ticket.id;
  try { message.ticket = await api.ticket(message.ticket.id); notify('处理进度已更新'); }
  catch (error) { showError(error); } finally { refreshing.value = ''; }
}
function resetChat() { ++conversationGeneration; messages.value = []; input.value = ''; busy.value = false; showTransfer.value = false; transferring.value = false; }
</script>
<template><div class="page-heading"><div><div class="eyebrow">CUSTOMER SERVICE</div><h1>智能客服<span class="heading-tag">订单与售后</span></h1><p>随时描述你的问题，复杂事项可转交人工处理。</p></div><button class="button secondary" @click="resetChat"><Icon name="plus" :size="17" />新对话</button></div><div class="chat-workspace"><section class="chat-panel"><header class="chat-panel-header"><div class="assistant-avatar"><Icon name="spark" :size="22" /></div><div><strong>订单服务助手</strong><small>回复由后端问答服务提供</small></div><span class="subtle-chip">AI ASSISTANT</span></header><div ref="scroller" class="message-list" aria-live="polite"><div v-if="messages.length === 0" class="chat-welcome"><div class="welcome-symbol"><Icon name="spark" :size="31" /></div><h2>你好，{{ auth.user?.name }}。</h2><p>关于订单、物流或售后，有什么可以帮你？</p><div class="suggestion-list"><button v-for="suggestion in suggestions" :key="suggestion" @click="send(suggestion)"><Icon :name="suggestion.includes('人工') ? 'headset' : suggestion.includes('退') ? 'clipboard' : 'truck'" :size="19" /><span>{{ suggestion }}</span><Icon name="plus" :size="15" /></button></div></div><div v-for="message in messages" :key="message.id" class="message" :class="message.role"><div class="message-avatar"><Icon v-if="message.role === 'assistant'" name="spark" :size="17" /><span v-else>{{ auth.user?.name.slice(0, 1) }}</span></div><div class="message-body"><small class="message-name">{{ message.role === 'assistant' ? '订单服务助手' : '我' }}</small><div class="message-bubble" :class="{ 'message-error': message.error }">{{ message.content }}</div><button v-if="message.route === 'transfer' && !message.ticket" class="button secondary transfer-button" @click="openTransfer(message)"><Icon name="headset" :size="17" />转人工客服</button><div v-if="message.ticket" class="ticket-card"><div class="ticket-card-title"><span><Icon name="clipboard" :size="18" />人工服务申请</span><StatusBadge :status="message.ticket.status" /></div><strong>{{ message.ticket.code }}</strong><p>{{ message.ticket.question }}</p><div v-if="message.ticket.status !== 'pending_review'" class="review-note">处理意见：{{ message.ticket.events.at(-1)?.note || '请等待客服进一步联系。' }}</div><div class="ticket-card-bottom"><small>{{ dateTime(message.ticket.created_at) }}</small><button :disabled="refreshing === message.ticket.id" @click="refreshTicket(message)"><Icon name="refresh" :size="14" />刷新进度</button></div></div></div></div><div v-if="busy" class="message assistant"><div class="message-avatar"><Icon name="spark" :size="17" /></div><div class="thinking"><span></span><span></span><span></span><small>正在处理你的问题</small></div></div></div><form class="chat-composer" @submit.prevent="send()"><textarea v-model="input" aria-label="输入你的问题" placeholder="输入订单问题，Enter 发送，Shift + Enter 换行…" maxlength="2000" rows="2" :disabled="busy" @keydown.enter.exact.prevent="send()"></textarea><div class="composer-footer"><small><Icon name="shield" :size="13" />请勿发送密码、验证码等敏感信息</small><button class="button primary" :disabled="busy || !input.trim()" type="submit"><Icon name="send" :size="16" />发送</button></div></form></section><aside class="service-aside"><div class="aside-card"><span class="eyebrow">SERVICE GUIDE</span><h3>服务就在身边</h3><div class="guide-item"><span><Icon name="box" :size="19" /></span><div><strong>订单咨询</strong><p>了解订单状态、商品与物流信息。</p></div></div><div class="guide-item"><span><Icon name="clipboard" :size="19" /></span><div><strong>售后申请</strong><p>描述问题并关联订单，方便客服核实。</p></div></div><div class="guide-item"><span><Icon name="headset" :size="19" /></span><div><strong>人工跟进</strong><p>复杂问题提交人工，随时刷新处理进度。</p></div></div></div><div class="aside-card human-card"><div class="human-icon"><Icon name="headset" :size="27" /></div><h3>需要进一步帮助？</h3><p>直接提交你的问题，<br>交由人工客服继续处理。</p><button class="button secondary" @click="openTransfer()">联系人工客服</button></div></aside></div><Modal v-if="showTransfer" title="提交人工服务申请" @close="!transferring && (showTransfer = false)"><form class="stack-form" @submit.prevent="transfer"><p class="form-hint">请描述需要处理的问题，关联订单可以帮助管理员更快核实。</p><label for="transfer-order">关联订单 <span class="muted">（可选）</span></label><select id="transfer-order" v-model="transferOrder"><option value="">不关联具体订单</option><option v-for="order in orders" :key="order.id" :value="order.id">{{ order.order_no }} · {{ order.items[0]?.name }}</option></select><label for="transfer-question">问题描述</label><textarea id="transfer-question" v-model="transferQuestion" required maxlength="2000" rows="5" placeholder="请详细描述需要客服处理的问题"></textarea><div class="modal-actions"><button type="button" class="button secondary" :disabled="transferring" @click="showTransfer = false">取消</button><button class="button primary" type="submit" :disabled="transferring || !transferQuestion.trim()">{{ transferring ? '正在提交…' : '提交申请' }}</button></div></form></Modal></template>
