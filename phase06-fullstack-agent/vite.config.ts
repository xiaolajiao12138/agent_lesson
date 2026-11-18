import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), vue()],
  // 两个 HTML 入口共用一个开发服务，生产构建也会同时生成两页。
  build: {
    rollupOptions: {
      input: ['index.html', 'vue.html'],
    },
  },
  server: {
    port: 5173
  }
})
