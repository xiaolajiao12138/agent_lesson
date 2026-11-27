<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { notice, notify } from './stores/notice';
import { logout } from './stores/auth';
const router = useRouter();
const expired = () => { logout(); router.replace('/login'); notify('登录已失效，请重新登录', 'error'); };
const apiError = (event: Event) => notify((event as CustomEvent<string>).detail, 'error');
onMounted(() => { window.addEventListener('app:unauthorized', expired); window.addEventListener('app:api-error', apiError); });
onUnmounted(() => { window.removeEventListener('app:unauthorized', expired); window.removeEventListener('app:api-error', apiError); });
</script>
<template><RouterView /><Transition name="toast"><div v-if="notice.text" class="toast" :class="notice.kind" role="status">{{ notice.text }}</div></Transition></template>
