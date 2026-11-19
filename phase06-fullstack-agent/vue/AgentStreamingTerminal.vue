<script setup lang="ts">
import { onUnmounted, ref } from 'vue'

interface ProgressEvent {
  stage: string
  message: string
}

interface ToolEvent {
  tool_name: string
  status: 'executing' | 'completed'
  summary?: string
}

interface UiEvent {
  component_type: 'UniversalMetricCard' | 'UniversalCompareCard' | 'UniversalTableCard' | 'UniversalConfirmCard' | string
  props: Record<string, any>
}

const apiBase = import.meta.env.VITE_AGENT_API_BASE_URL || 'http://127.0.0.1:8019'
const prompt = ref('分析 2026 年新能源汽车出海战略')
const isRunning = ref(false)
const progress = ref<ProgressEvent[]>([])
const tools = ref<ToolEvent[]>([])
const cards = ref<UiEvent[]>([])
const answer = ref('')
const error = ref('')
const approvalStates = ref<Record<string, 'approved' | 'rejected'>>({})

let stream: EventSource | null = null

function closeStream() {
  stream?.close()
  stream = null
  isRunning.value = false
}

function attachListeners(connection: EventSource) {
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
  listen<UiEvent>('generative_ui', (payload) => {
    cards.value.push(payload)
  })
  listen<{ delta: string }>('message_chunk', ({ delta }) => {
    answer.value += delta
  })

  connection.addEventListener('done', () => {
    if (stream === connection) closeStream()
  })
  connection.onerror = () => {
    if (stream !== connection) return
    error.value = '连接已中断。请确认 Day 19 后端正在运行，再重试。'
    closeStream()
  }
}

function startTask(customPrompt?: string) {
  if (typeof customPrompt === 'string') {
    prompt.value = customPrompt
  }
  const request = prompt.value.trim()
  if (!request || isRunning.value) return

  progress.value = []
  tools.value = []
  cards.value = []
  answer.value = ''
  error.value = ''
  isRunning.value = true

  try {
    const url = new URL('/api/agent/stream', apiBase)
    url.searchParams.set('prompt', request)
    const connection = new EventSource(url)
    stream = connection
    attachListeners(connection)
  } catch {
    error.value = '无法连接。请检查后端地址配置。'
    closeStream()
  }
}

function handleApprovalDecision(approvalId: string, decision: 'approved' | 'rejected') {
  if (!approvalId) return
  approvalStates.value[approvalId] = decision
  closeStream()
  answer.value = ''
  isRunning.value = true

  const url = new URL('/api/agent/approval/stream', apiBase)
  url.searchParams.set('approval_id', approvalId)
  url.searchParams.set('decision', decision)
  const connection = new EventSource(url)
  stream = connection
  attachListeners(connection)
}

onUnmounted(closeStream)
</script>

<template>
  <main class="mx-auto my-8 max-w-3xl rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <header class="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-slate-900">全栈 Agent 工作台 (企业级“四大万能模板”架构)</h1>
        <p class="mt-1 text-sm text-slate-500">Vue 3 · FastAPI SSE · 5 大工具归一映射 4 大通用模板</p>
      </div>
      <span role="status" class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
        {{ isRunning ? '执行中' : '就绪' }}
      </span>
    </header>

    <div class="mb-3 flex flex-wrap items-center gap-2">
      <span class="text-xs text-slate-400">一键测试 5 大工具 ➔ 4 大模板：</span>
      <button
        type="button"
        :disabled="isRunning"
        class="rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
        @click="startTask('分析 2026 年新能源汽车出海战略')"
      >
        📊 行业指标 (走模板1)
      </button>
      <button
        type="button"
        :disabled="isRunning"
        class="rounded-lg bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-100 disabled:opacity-50"
        @click="startTask('深圳今天天气怎么样？出门穿什么衣服合适？')"
      >
        🌤️ 城市天气 (共用模板1!)
      </button>
      <button
        type="button"
        :disabled="isRunning"
        class="rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
        @click="startTask('请把“前端工程师转型 AI Agent 开发具有天然的全栈交互与状态机优势”翻译成地道英文')"
      >
        🌐 多语种翻译 (走模板2)
      </button>
      <button
        type="button"
        :disabled="isRunning"
        class="rounded-lg bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-50"
        @click="startTask('请用表格对比 LangGraph、AutoGen、CrewAI 三大主流 Agent 框架的核心优势与适用场景')"
      >
        📋 框架对比表 (走模板3)
      </button>
      <button
        type="button"
        :disabled="isRunning"
        class="rounded-lg bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-50"
        @click="startTask('请帮我将 agent-web-portal 项目发布上线到 prod 生产环境，镜像版本 v2.4.0')"
      >
        🛡️ 高危发布审批 (走模板4)
      </button>
    </div>

    <form class="mb-6 flex flex-col gap-3 sm:flex-row" @submit.prevent="startTask()">
      <label class="sr-only" for="agent-prompt">任务描述</label>
      <input
        id="agent-prompt"
        v-model="prompt"
        type="text"
        placeholder="输入指标分析、天气、翻译、表格对比、或高危发布审批指令..."
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

    <!-- 四大万能模板统一渲染区 -->
    <template v-for="(card, index) in cards" :key="index">
      <!-- 模板 1：UniversalMetricCard -->
      <article
        v-if="card.component_type === 'UniversalMetricCard'"
        class="my-4 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/60 via-white to-blue-50/40 p-5 shadow-sm"
      >
        <header class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-bold text-gray-800">{{ card.props.title }}</h3>
          <span class="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
            {{ card.props.badge }} · 模板1
          </span>
        </header>
        <div class="mb-3 grid gap-3" :class="(card.props.items?.length || 0) >= 3 ? 'grid-cols-3' : 'grid-cols-2'">
          <div v-for="(item, idx) in card.props.items" :key="idx" class="rounded-xl border border-gray-100 bg-white p-3">
            <div class="mb-1 text-xs text-gray-500">{{ item.label }}</div>
            <div class="font-mono text-2xl font-black text-indigo-600">{{ item.value }}</div>
            <div v-if="item.subtext" class="mt-0.5 text-xs text-gray-500">{{ item.subtext }}</div>
          </div>
        </div>
        <p v-if="card.props.notice" class="rounded-lg border border-amber-200/60 bg-amber-50/80 p-2.5 text-xs text-amber-800">
          {{ card.props.notice }}
        </p>
      </article>

      <!-- 模板 2：UniversalCompareCard -->
      <article
        v-else-if="card.component_type === 'UniversalCompareCard'"
        class="my-4 rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50/70 via-white to-teal-50/40 p-5 shadow-sm"
      >
        <header class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-bold text-gray-800">{{ card.props.title }}</h3>
          <span class="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            {{ card.props.badge }} · 模板2
          </span>
        </header>
        <div class="space-y-2.5">
          <div class="rounded-xl border border-gray-100 bg-white/80 p-3">
            <div class="mb-1 text-[11px] text-gray-400">{{ card.props.source_title }}</div>
            <div class="text-xs text-gray-600">{{ card.props.source_content }}</div>
          </div>
          <div class="rounded-xl border border-emerald-200 bg-white p-3.5">
            <div class="mb-1 text-[11px] font-semibold text-emerald-600">{{ card.props.target_title }}</div>
            <div class="text-base font-bold text-gray-900">{{ card.props.target_content }}</div>
          </div>
        </div>
      </article>

      <!-- 模板 3：UniversalTableCard -->
      <article
        v-else-if="card.component_type === 'UniversalTableCard'"
        class="my-4 rounded-2xl border border-purple-100 bg-gradient-to-br from-purple-50/50 via-white to-indigo-50/30 p-5 shadow-sm"
      >
        <header class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-bold text-gray-800">{{ card.props.title }}</h3>
          <span class="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700">
            {{ card.props.badge }} · 模板3
          </span>
        </header>
        <div class="mb-3 overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table class="w-full border-collapse text-left text-xs">
            <thead>
              <tr class="border-b border-gray-200 bg-gray-50 font-bold text-gray-600">
                <th v-for="(col, cIdx) in card.props.columns" :key="cIdx" class="px-3 py-2.5">{{ col }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="(row, rIdx) in card.props.rows" :key="rIdx">
                <td v-for="(cell, cellIdx) in row" :key="cellIdx" class="px-3 py-2.5 text-gray-700">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="card.props.summary" class="rounded-lg border border-purple-200/60 bg-purple-50/80 p-2.5 text-xs text-purple-900">
          💡 {{ card.props.summary }}
        </p>
      </article>

      <!-- 模板 4：UniversalConfirmCard -->
      <article
        v-else-if="card.component_type === 'UniversalConfirmCard'"
        class="my-4 rounded-2xl border-2 border-rose-200 bg-gradient-to-br from-rose-50/60 via-white to-amber-50/30 p-5 shadow-sm"
      >
        <header class="mb-2 flex items-center justify-between">
          <h3 class="text-base font-bold text-gray-900">{{ card.props.title }}</h3>
          <span class="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-medium text-rose-700">
            {{ card.props.badge }} · 模板4
          </span>
        </header>
        <p class="mb-3 text-xs text-gray-600">{{ card.props.description }}</p>
        <div class="mb-3 space-y-1.5 rounded-xl border border-rose-100 bg-white p-3">
          <div v-for="(d, dIdx) in card.props.details" :key="dIdx" class="flex justify-between text-xs">
            <span class="text-gray-500">{{ d.label }}：</span>
            <span class="font-semibold text-gray-800">{{ d.value }}</span>
          </div>
        </div>
        <div class="flex justify-end gap-2.5 border-t border-rose-100 pt-2">
          <template v-if="!approvalStates[card.props.approval_id]">
            <button
              type="button"
              class="rounded-lg bg-gray-100 px-3.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200"
              @click="handleApprovalDecision(card.props.approval_id, 'rejected')"
            >
              ✕ 驳回拦截 (通知后台中止)
            </button>
            <button
              type="button"
              class="rounded-lg bg-rose-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-rose-700"
              @click="handleApprovalDecision(card.props.approval_id, 'approved')"
            >
              ✓ 批准并授权后台执行
            </button>
          </template>
          <span v-else class="text-xs font-bold text-emerald-700">
            已提交决定 ({{ approvalStates[card.props.approval_id] }})，后台已恢复执行下一步
          </span>
        </div>
      </article>
    </template>

    <section
      v-if="answer"
      aria-label="Agent 回复"
      class="mt-4 whitespace-pre-wrap break-words rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 text-sm leading-7 text-slate-800"
    >{{ answer }}</section>
  </main>
</template>
