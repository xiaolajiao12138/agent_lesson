<script setup lang="ts">
import type { Order } from '../types';
import { money, dateTime } from '../utils/format';
import StatusBadge from './StatusBadge.vue';
defineProps<{ order: Order }>();
</script>
<template><div class="order-detail"><div class="detail-heading"><div><span class="eyebrow">ORDER DETAILS</span><h3>{{ order.order_no }}</h3></div><StatusBadge :status="order.status" /></div><div class="detail-grid"><div><span>客户姓名</span><strong>{{ order.customer_name }}</strong></div><div><span>联系电话</span><strong>{{ order.phone }}</strong></div><div><span>创建时间</span><strong>{{ dateTime(order.created_at) }}</strong></div><div><span>物流单号</span><strong>{{ order.tracking_no || '暂无物流信息' }}</strong></div></div><div class="address"><span>收货地址</span><p>{{ order.address }}</p></div><div v-for="item in order.items" :key="item.sku" class="product-row"><div class="product-icon">{{ item.name.slice(0, 1) }}</div><div class="grow"><strong>{{ item.name }}</strong><small>{{ item.sku }} · 数量 {{ item.quantity }}</small></div><strong>{{ money(item.price_cents * item.quantity) }}</strong></div><div class="total-row"><span>订单金额</span><strong>{{ money(order.total_cents) }}</strong></div></div></template>
