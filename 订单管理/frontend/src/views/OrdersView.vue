<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { api } from '../api';
import type { Order, Page } from '../types';
import { dateTime, money, orderLabels } from '../utils/format';
import { showError } from '../stores/notice';
import Icon from '../components/Icon.vue';
import StatusBadge from '../components/StatusBadge.vue';
import Modal from '../components/Modal.vue';
import OrderDetail from '../components/OrderDetail.vue';
const result = ref<Page<Order>>({ items: [], total: 0, page: 1, page_size: 8 });
const q = ref(''), status = ref(''), loading = ref(false), errorText = ref(''), selected = ref<Order | null>(null);
const totalAmount = computed(() => result.value.items.reduce((sum, item) => sum + item.total_cents, 0));
const paidCount = computed(() => result.value.items.filter(item => item.status === 'paid').length);
let generation = 0;
async function load(page = 1) {
  const current = ++generation; loading.value = true; errorText.value = '';
  try { const data = await api.orders({ q: q.value, status: status.value, page, page_size: 8 }); if (current === generation) result.value = data; }
  catch (error) { if (current === generation) errorText.value = error instanceof Error ? error.message : '加载失败'; }
  finally { if (current === generation) loading.value = false; }
}
let detailGeneration = 0;
async function openDetail(id: string) {
  const generation = ++detailGeneration;
  try { const data = await api.order(id); if (generation === detailGeneration) selected.value = data; }
  catch (error) { if (generation === detailGeneration) showError(error); }
}
function closeDetail() { ++detailGeneration; selected.value = null; }
onMounted(() => load());
</script>
<template><div class="page-heading"><div><div class="eyebrow">ORDER MANAGEMENT</div><h1>订单查询</h1><p>查找订单、核对商品信息，跟进每一笔订单的状态。</p></div><button class="button secondary" :disabled="loading" @click="load(result.page)"><Icon name="refresh" :size="17" />刷新数据</button></div><div class="stats-grid"><div class="stat-card"><div><span>查询结果</span><strong>{{ result.total }}<small>笔订单</small></strong></div><div class="stat-symbol blue"><Icon name="box" :size="23" /></div></div><div class="stat-card"><div><span>本页待发货</span><strong>{{ paidCount }}<small>笔待跟进</small></strong></div><div class="stat-symbol amber"><Icon name="truck" :size="23" /></div></div><div class="stat-card"><div><span>本页订单金额</span><strong class="money-stat">{{ money(totalAmount) }}</strong></div><div class="stat-symbol green"><Icon name="file" :size="23" /></div></div></div><section class="table-card"><header class="section-header"><div><h2>订单列表 <span class="count-chip">{{ result.total }}</span></h2><p>按订单号、客户或商品快速查找</p></div><span class="muted section-caption">数据按当前查询条件展示</span></header><form class="filter-bar" @submit.prevent="load()"><div class="search-field"><Icon name="search" :size="18" /><input v-model="q" aria-label="搜索订单" placeholder="订单号 / 客户姓名 / 商品名称" /></div><select v-model="status" aria-label="订单状态" @change="load()"><option value="">全部订单状态</option><option v-for="(label, value) in orderLabels" :key="value" :value="value">{{ label }}</option></select><button class="button primary" :disabled="loading" type="submit">查询订单</button><button class="button text" type="button" @click="q = ''; status = ''; load()">重置</button></form><div v-if="errorText" class="empty-state error-state"><Icon name="file" :size="36" /><h3>暂时无法加载订单</h3><p>{{ errorText }}</p><button class="button secondary" @click="load()">重新加载</button></div><div v-else class="table-scroll" :class="{ 'is-loading': loading }"><table><thead><tr><th>订单 / 商品</th><th>客户</th><th>订单金额</th><th>订单状态</th><th>创建时间</th><th class="align-right">操作</th></tr></thead><tbody><tr v-for="order in result.items" :key="order.id"><td><div class="order-cell"><span class="product-thumb"><Icon name="box" :size="22" /></span><div><strong>{{ order.order_no }}</strong><small>{{ order.items[0]?.name }}<span v-if="order.items.length > 1"> 等 {{ order.items.length }} 件商品</span></small></div></div></td><td><div class="customer-cell"><strong>{{ order.customer_name }}</strong><small>{{ order.phone }}</small></div></td><td class="amount-cell">{{ money(order.total_cents) }}</td><td><StatusBadge :status="order.status" /></td><td class="date-cell">{{ dateTime(order.created_at) }}</td><td class="align-right"><button class="table-action" @click="openDetail(order.id)">查看详情</button></td></tr></tbody></table><div v-if="!result.items.length && !loading" class="empty-state"><Icon name="search" :size="37" /><h3>没有找到相关订单</h3><p>调整关键词或订单状态后再试试。</p></div><div v-if="loading" class="table-loading"><span class="spinner"></span>正在加载订单…</div></div><footer class="pagination"><span>共 {{ result.total }} 条记录，每页 {{ result.page_size }} 条</span><div><button class="button secondary small-button" :disabled="loading || result.page <= 1" @click="load(result.page - 1)">上一页</button><span>{{ result.page }} / {{ Math.max(1, Math.ceil(result.total / result.page_size)) }}</span><button class="button secondary small-button" :disabled="loading || result.page * result.page_size >= result.total" @click="load(result.page + 1)">下一页</button></div></footer></section><div class="page-footnote"><Icon name="shield" :size="15" />订单查询用于核对信息，服务申请请前往审批中心处理。</div><Modal v-if="selected" title="订单详情" wide @close="closeDetail()"><OrderDetail :order="selected" /></Modal></template>
