<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import MetricDashboardCard from './MetricDashboardCard.vue'

interface ProgressEvent {
  stage: string
  message: string
}

interface ToolEvent {
  tool_name: string
  status: 'executing' | 'completed'
  summary?: string
}

// Day 19｜把后端协议中的组件名映射到本地组件。只渲染已注册的类型。
type MetricProps = InstanceType<typeof MetricDashboardCard>['$props']
interface UiEvent {
  component_type: string
  props: MetricProps
}

const apiBase = import.meta.env.VITE_AGENT_API_BASE_URL || 'http://127.0.0.2:8019'
const prompt = ref('分析 2026 年新能源汽车出海战略')
const isRunning = ref(false)
const progress = ref<ProgressEvent[]>([])
const tools = ref<ToolEvent[]>([])
const cards = ref<MetricProps[]>([])
const answer = ref('')
const error = ref('')

// EventSource 是浏览器对象，模板只需要观察 isRunning 等 ref。
let stream: EventSource | null = null

function closeStream() {
  stream?.close()
  stream = null
  isRunning.value = false
}

function startTask() {
  const request = prompt.value.trim()
  if (!request || isRunning.value) return

  progress.value = []
  tools.value = []
  cards.value = []
  answer.value = ''
  error.value = ''
  isRunning.value = true

  try {
    // Day 19｜URLSearchParams 会编码中文、空格和 &，使整段提示词留在 prompt 参数中。
    const url = new URL('/api/agent/stream', apiBase)
    url.searchParams.set('prompt', request)
    const connection = new EventSource(url)
    stream = connection

    // named SSE events 对应 FastAPI 里的 event 字段，data 仍需解析为 JSON。
    function listen<T>(event: string, apply: (payload: T) => void) {
      connection.addEventListener(event, (message: MessageEvent<string>) => {
        if (stream !== connection) return
        try {
          apply(JSON.parse(message.data) as T)
        } catch {
          error.value = '收到无法读取的响应，任务已停止。'
          closeStream()
        }
      })
    }

    listen<ProgressEvent>('thought', (payload) => {
      progress.value.push(payload)
      if (payload.stage === 'error') error.value = payload.message
    })
    listen<ToolEvent>('tool_call', (payload) => tools.value.push(payload))
    listen<UiEvent>('generative_ui', ({ component_type, props }) => {
      if (component_type === 'MetricDashboardCard') cards.value.push(props)
    })
    listen<{ delta: string }>('message_chunk', ({ delta }) => {
      answer.value += delta
    })

    // 主动关闭可避免 EventSource 在流结束或失败后自动重连并重复发起任务。
    connection.addEventListener('done', () => {
      if (stream === connection) closeStream()
    })
    connection.onerror = () => {
      if (stream !== connection) return
      error.value = '连接已中断。请确认 Day 19 后端正在运行，再重试。'
      closeStream()
    }
  } catch {
    error.value = '无法连接。请检查后端地址配置。'
    closeStream()
  }
}

onUnmounted(closeStream)
</script>

<template>
  <main class="mx-auto my-8 max-w-3xl rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <header class="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-slate-900">全栈 Agent 工作台</h1>
        <p class="mt-1 text-sm text-slate-500">Vue 3 · FastAPI SSE</p>
      </div>
      <span role="status" class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
        {{ isRunning ? '执行中' : '就绪' }}
      </span>
    </header>

    <form class="mb-6 flex flex-col gap-3 sm:flex-row" @submit.prevent="startTask">
      <label class="sr-only" for="agent-prompt">任务描述</label>
      <input
        id="agent-prompt"
        v-model="prompt"
        type="text"
        placeholder="输入你希望 Agent 分析的任务"
        class="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-100"
      />
      <button
        type="submit"
        :disabled="isRunning || !prompt.trim()"
        class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:bg-slate-400"
      >
        发起 Agent 任务
      </button>
    </form>

    <p v-if="error" role="alert" class="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      {{ error }}
    </p>

    <section v-if="progress.length" aria-label="执行进度" class="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <h2 class="mb-2 text-sm font-semibold text-slate-800">执行进度</h2>
      <ul class="space-y-1 break-words text-sm text-slate-700">
        <li v-for="(event, index) in progress" :key="index">{{ event.message }}</li>
      </ul>
    </section>

    <section v-if="tools.length" aria-label="工具调用" class="mb-4 rounded-xl border border-blue-100 bg-blue-50 p-4">
      <h2 class="mb-2 text-sm font-semibold text-blue-900">工具调用</h2>
      <ul class="space-y-1 break-words text-sm text-blue-800">
        <li v-for="(event, index) in tools" :key="index">
          <code>{{ event.tool_name }}</code>
          · {{ event.status === 'completed' ? '已完成' : '执行中' }}
          <span v-if="event.summary"> · {{ event.summary }}</span>
        </li>
      </ul>
    </section>

    <MetricDashboardCard v-for="(card, index) in cards" :key="index" v-bind="card" />

    <section
      v-if="answer"
      aria-label="Agent 回复"
      class="mt-4 whitespace-pre-wrap break-words rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 text-sm leading-7 text-slate-800"
    >{{ answer }}</section>
  </main>
</template>
