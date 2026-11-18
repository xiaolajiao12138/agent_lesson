<script setup lang="ts">
import { ref } from 'vue';

// Day 19 的 generative_ui 事件通过 props 提供卡片内容，字段与后端协议一致。
interface MetricCardProps {
  title: string;
  metric1_label?: string;
  penetration_rate: string;
  metric2_label?: string;
  export_growth: string;
  risk_warning: string;
  tags: string[];
}

withDefaults(defineProps<MetricCardProps>(), {
  metric1_label: '核心指标 1',
  metric2_label: '核心指标 2',
});

// 每个卡片实例用 ref 保存自己的自选状态，模板会随状态更新。
const isFollowed = ref(false);
</script>

<template>
  <article
    class="my-4 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/60 via-white to-blue-50/40 p-5 shadow-sm transition-shadow hover:shadow-md"
  >
    <header class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h3 class="flex items-center gap-2 text-base font-bold text-gray-800">
        <span aria-hidden="true" class="h-2 w-2 shrink-0 rounded-full bg-indigo-600 motion-safe:animate-pulse"></span>
        {{ title }}
      </h3>
      <span class="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
        Generative UI 动态组件
      </span>
    </header>

    <dl class="mb-3 grid grid-cols-2 gap-3">
      <div class="min-w-0 rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
        <dt class="mb-1 text-xs text-gray-500">{{ metric1_label }}</dt>
        <dd class="break-words font-mono text-2xl font-black text-indigo-600">{{ penetration_rate }}</dd>
      </div>
      <div class="min-w-0 rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
        <dt class="mb-1 text-xs text-gray-500">{{ metric2_label }}</dt>
        <dd class="break-words font-mono text-2xl font-black text-emerald-600">{{ export_growth }}</dd>
      </div>
    </dl>

    <p class="mb-3 rounded-lg border border-amber-200/60 bg-amber-50/80 p-2.5 text-xs text-amber-800">
      <strong>[风险关注]</strong> {{ risk_warning }}
    </p>

    <footer class="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 pt-2">
      <ul class="flex flex-wrap gap-1.5">
        <li v-for="(tag, index) in tags" :key="index" class="rounded-md bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600">
          #{{ tag }}
        </li>
      </ul>
      <button
        type="button"
        :aria-pressed="isFollowed"
        class="rounded-lg px-3 py-1.5 text-xs font-medium text-white shadow-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        :class="isFollowed ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-indigo-600 hover:bg-indigo-700'"
        @click="isFollowed = !isFollowed"
      >
        {{ isFollowed ? '✓ 已订阅监控' : '+ 加入大盘自选' }}
      </button>
    </footer>
  </article>
</template>
