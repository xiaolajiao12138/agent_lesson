# 阶段一：LLM 核心概念与 Prompt 工程（第 1 ~ 2 周）

## 🎯 阶段学习目标
1. 彻底理解大语言模型（LLM）的输入输出机制与核心参数。
2. 掌握 Prompt 结构化设计技巧与防止幻觉的基本方法。
3. 掌握 **结构化输出（Structured Output / JSON Mode）**，让模型输出严格符合前端 UI 要求的格式。
4. 掌握 **SSE（Server-Sent Events）** 流式通信，实现极致的打字机交互效果。

---

## 📚 1. 核心概念速记表

| 概念 | 核心理解 | 实际开发影响 |
| :--- | :--- | :--- |
| **Token** | 模型的最小计算单元，1 个汉字通常占用 1~2 个 Token，英文单词约 0.75 Token。 | 直接决定 API 计费成本和处理速度。 |
| **Context Window（上下文窗口）** | 模型单次对话能容纳的最大 Token 数（包括输入与输出）。 | 决定了一次对话最多能给模型塞入多少上下文/历史记录。 |
| **Temperature（温度）** | 控制输出的随机性，取值范围 `0 ~ 2`。 | 严谨的数据提取/SQL生成/参数提取设为 `0`；头脑风暴/文案创作设为 `0.7 ~ 1.0`。 |
| **Top_P（核采样）** | 另一种控制多样性的参数，通常与 Temperature 二选一调整。 | 建议保持默认 `1.0`，主要调整 Temperature 即可。 |
| **System Prompt（系统提示）** | 对模型的全局指令与人设、原则限制。 | 决定了 Agent 的性格、工作职责和输出约束规范。 |

---

## 🛠️ 2. Prompt 工程核心技巧（让输出听话）

模型不是读心术，模糊的指令产生模糊的结果。编写生产级 Prompt 的“四要素模型”：

```markdown
1. 【角色设定（Role）】：你是一名资深的全栈架构师，具备严谨的代码审查规范。
2. 【任务目标（Goal）】：请对用户提供的前端代码片段进行代码异味（Code Smell）检测。
3. 【约束条件（Constraint）】：
   - 只指出潜在的性能问题与内存泄露风险；
   - 严禁输出无关寒暄语；
   - 必须以严格的 JSON 格式输出。
4. 【输出格式（Format）】：输出字段必须包含 issues（数组），每个元素包含 line、severity、suggestion。
```

---

## 💻 3. 结构化输出：让 AI 与前端组件完美对接

大模型默认输出非结构化的 Markdown 或纯文本。但在企业级应用中，我们需要让 AI 输出精准的 JSON，以驱动前端渲染特定的 UI 卡片。

### Node.js / TypeScript 示例（使用 OpenAI SDK + Zod）

```typescript
import OpenAI from "openai";
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// 1. 定义期望的返回格式 (Zod Schema)
const TaskSchema = z.object({
  title: z.string().describe("任务简短标题"),
  priority: z.enum(["low", "medium", "high"]).describe("优先级"),
  estimatedHours: z.number().describe("预估耗时(小时)"),
  subtasks: z.array(z.string()).describe("子任务列表"),
});

// 2. 强制模型严格遵守此 Schema 输出
async function generateTaskPlan(requirement: string) {
  const completion = await openai.beta.chat.completions.parse({
    model: "gpt-4o-mini", // 或其他支持 structured outputs 的模型
    messages: [
      { role: "system", content: "你是一个项目任务拆解专家。" },
      { role: "user", content: requirement },
    ],
    response_format: zodResponseFormat(TaskSchema, "task_plan"),
  });

  const plan = completion.choices[0].message.parsed;
  console.log("解析后的结构化数据：", plan);
  return plan;
}
```

---

## 🌊 4. 流式传输（SSE）与打字机效果

大模型生成长文本通常耗时 5~15 秒，绝对不能等完全生成才返回给前端，必须使用 **SSE（Server-Sent Events）**。

### 原理简析
* 前端向后端发起 HTTP 请求，`Accept: text/event-stream`；
* 后端保持长连接，以 `data: chunk\n\n` 格式源源不断推送文字增量；
* 前端通过 `ReadableStream` 或 `EventSource` 逐步将文本拼接到页面上。

### 前端最省力利器：Vercel AI SDK
在 Next.js / React 中，只需几行代码即可集成流式对话与打字机：

```tsx
"use client";
import { useChat } from "ai/react";

export default function ChatComponent() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat();

  return (
    <div className="p-4 max-w-xl mx-auto">
      <div className="space-y-4 mb-4">
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "text-blue-600" : "text-green-700"}>
            <strong>{m.role === "user" ? "我: " : "AI: "}</strong>
            <span className="whitespace-pre-wrap">{m.content}</span>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="问点什么..."
          className="border p-2 flex-1 rounded"
        />
        <button type="submit" disabled={isLoading} className="bg-blue-500 text-white px-4 py-2 rounded">
          {isLoading ? "生成中..." : "发送"}
        </button>
      </form>
    </div>
  );
}
```

---

## 📋 阶段一实战作业

1. **环境准备**：
   - 申请一个国内模型 API Key（推荐 DeepSeek、智谱或月之暗面 Kimi，网络更稳定，且兼容 OpenAI SDK 格式）。
2. **动手实践**：
   - 使用 Next.js / React 跑通上述流式对话代码。
   - 练习编写 3 个不同场景的 System Prompt（代码审查助手、中英文互译助手、周报润色助手）。
   - 验证结构化输出：让模型总结一段需求，并保证返回纯 JSON 格式驱动前端展示为表格。
