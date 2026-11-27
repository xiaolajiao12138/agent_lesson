<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue';
import Icon from './Icon.vue';
defineProps<{ title: string; wide?: boolean }>();
const emit = defineEmits<{ close: [] }>();
const panel = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null, previousOverflow = '';
const focusable = () => Array.from(panel.value?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]') || []);
function handleKey(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); emit('close'); }
  if (event.key === 'Tab') {
    const nodes = focusable(), first = nodes[0], last = nodes.at(-1);
    if (!first || !last) { event.preventDefault(); panel.value?.focus(); return; }
    if (event.shiftKey && (document.activeElement === first || !panel.value?.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
}
onMounted(async () => {
  previousFocus = document.activeElement as HTMLElement;
  previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden';
  window.addEventListener('keydown', handleKey); await nextTick();
  (panel.value?.querySelector<HTMLElement>('input, textarea, select') || focusable()[0] || panel.value)?.focus();
});
onUnmounted(() => { window.removeEventListener('keydown', handleKey); document.body.style.overflow = previousOverflow; if (previousFocus?.isConnected) previousFocus.focus(); });
</script>
<template><Teleport to="body"><div class="modal-overlay" @click.self="emit('close')"><section ref="panel" tabindex="-1" class="modal" :class="{ wide }" role="dialog" aria-modal="true" :aria-label="title"><header><h2>{{ title }}</h2><button class="icon-button" aria-label="关闭弹窗" @click="emit('close')"><Icon name="x" /></button></header><div class="modal-content"><slot /></div></section></div></Teleport></template>
