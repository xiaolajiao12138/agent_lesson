<script setup lang="ts">
import { orderLabels, reviewLabels } from '../utils/format';
import type { OrderStatus, ReviewStatus } from '../types';
defineProps<{ status: OrderStatus | ReviewStatus }>();
const labels: Record<string, string> = { ...orderLabels, ...reviewLabels };
</script>
<template><span class="status-badge" :class="status"><span></span>{{ labels[status] || status }}</span></template>
