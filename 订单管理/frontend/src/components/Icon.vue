<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number }>(), { size: 20 });
const paths: Record<string, string> = {
  box: 'M12 3 3 7.5v9L12 21l9-4.5v-9L12 3ZM3 7.5l9 4.5 9-4.5M12 12v9M7.5 5.25l9 4.5',
  chat: 'M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-1 1V11.5A8.5 8.5 0 0 1 21 11.5ZM7 10h10M7 14h6',
  check: 'm5 12 4 4L19 6',
  clipboard: 'M9 5H6a2 2 0 0 0-2 2v13h16V7a2 2 0 0 0-2-2h-3M9 3h6v4H9V3Zm-1 12 3 3 5-6',
  search: 'M20 20l-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z',
  logout: 'M9 3H4v18h5M10 12h11m-4-4 4 4-4 4',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  lock: 'M5 10h14v11H5V10ZM8 10V7a4 4 0 0 1 8 0v3M12 14v3',
  eye: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  spark: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z',
  send: 'm21 3-7 18-4-7-7-4 18-7ZM10 14 21 3',
  headset: 'M3 14v-2a9 9 0 0 1 18 0v2M3 12h4v8H3v-8Zm14 0h4v8h-4v-8Zm4 8c0 2-4 2-7 2',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v5l3 2',
  refresh: 'M20 8a8 8 0 1 0 0 8M20 3v5h-5',
  x: 'm6 6 12 12M6 18 18 6',
  down: 'm6 9 6 6 6-6',
  plus: 'M12 5v14M5 12h14',
  truck: 'M2 5h12v12H2V5Zm12 5h4l4 4v3h-8M7 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm14 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z',
  file: 'M5 3h9l5 5v13H5V3Zm9 0v5h5M8 12h8M8 16h6',
  shield: 'm12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Zm-4 10 3 3 5-6',
  menu: 'M4 6h16M4 12h16M4 18h16',
};
</script>
<template><svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.box" /></svg></template>
