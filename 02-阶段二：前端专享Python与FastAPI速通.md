# 阶段二：前端专享 Python 与 FastAPI 速通（第 3 周）

## 🎯 阶段学习目标
1. 消除对 Python 的陌生感，用前端（JS/TS）现成经验 3 天内掌握 Python 核心编程。
2. 告别老旧繁琐的配置，直接掌握现代化极速包管理工具：**`uv`**（Python 版的 pnpm）。
3. 掌握 **Pydantic**（Python 版的 Zod），掌握严格的数据模型与校验。
4. 掌握 **FastAPI**，编写高性能异步微服务及 SSE 流式接口，为承接 Agent 后台做好准备。

---

## ⚡ 1. 现代化工具链准备：告别 Anaconda，拥抱 `uv`

在过去，Python 环境混乱（pip、virtualenv、conda）劝退了无数初学者。现在业界最推崇的是由 Rust 编写的高性能工具 **`uv`**（类似 JavaScript 世界的 `pnpm` 或 `bun`）。

### 安装与快速启动
在 Windows PowerShell 中安装：
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

初始化一个 Python Agent 项目：
```powershell
# 1. 创建项目目录
uv init agent-backend
cd agent-backend

# 2. 创建并激活虚拟环境（类似 node_modules 的独立环境隔离）
uv venv
.venv\Scripts\activate

# 3. 安装依赖（快如闪电）
uv add fastapi uvicorn pydantic openai
```

---

## 🔄 2. 前端视角：JS/TS vs Python 极速对照表

| 场景 | JavaScript / TypeScript | Python 对应写法 |
| :--- | :--- | :--- |
| **控制台打印** | `console.log("Hello", name);` | `print(f"Hello {name}")` (推荐 f-string) |
| **数组 / 列表** | `const list = [1, 2, 3];` | `my_list = [1, 2, 3]` |
| **对象 / 字典** | `const obj = { name: "Tom", age: 18 };` | `obj = {"name": "Tom", "age": 18}` |
| **数组遍历映射**| `arr.map(x => x * 2);` | `[x * 2 for x in arr]` (列表推导式) |
| **解构 / 展开** | `{ ...obj, newKey: 1 }` | `{**obj, "newKey": 1}` |
| **异步函数** | `async function fetchDoc() {}` | `async def fetch_doc():` |
| **等待异步** | `const res = await fetch();` | `res = await fetch()` |
| **类型声明** | `function add(a: number): number` | `def add(a: int) -> int:` |

> [!TIP]
> Python 没有大括号 `{}`，通过**缩进（通常是 4 个空格）**来决定代码块层级。注意不要混用空格与 Tab。

---

## 🛡️ 3. Pydantic 实战：Python 版本的 Zod

在开发 Agent 时，我们必须对大模型的输入和输出做强类型校验。Pydantic 就是 Python 世界的 Zod：

```python
from pydantic import BaseModel, Field
from typing import List, Optional

# 定义用户与 Agent 交互的请求体模型
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的提问内容")
    model: Optional[str] = Field(default="gpt-4o-mini", description="指定调用的模型")
    history_limit: int = Field(default=5, ge=1, le=20, description="携带的历史对话轮数")

# 定义 Agent 意图识别的输出模型
class IntentExtraction(BaseModel):
    intent: str = Field(..., description="识别出的用户意图: chat | search | execute_tool")
    confidence: float = Field(..., description="置信度 0~1")
    tags: List[str] = Field(default=[], description="关键词标签")

# 尝试解析
raw_data = {"intent": "search", "confidence": 0.95, "tags": ["AI", "Agent"]}
intent_obj = IntentExtraction(**raw_data)
print(intent_obj.intent)  # "search"
```

---

## 🚀 4. FastAPI：快速搭建全异步的 AI 后端微服务

FastAPI 是目前 Python 生态下编写 Agent 服务、微服务和高并发接口的第一选择，它天然支持 `async/await`，自带 Swagger 文档。

### 搭建带有 SSE 流式响应的接口 (`main.py`)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json

app = FastAPI(title="Agent 核心服务 API")

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryPayload(BaseModel):
    question: str

async def fake_llm_stream(question: str):
    """模拟大模型逐字打字流式输出"""
    chunks = [f"你好！", f"关于你的提问：'{question}'，", "正在思考中...", "Agent 正在调集后台工具...", "处理完毕！"]
    for chunk in chunks:
        # SSE 规范格式：data: 内容\n\n
        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.5)

@app.post("/api/chat/stream")
async def chat_stream(payload: QueryPayload):
    return StreamingResponse(fake_llm_stream(payload.question), media_type="text/event-stream")

# 运行命令：uv run uvicorn main:app --reload --port 8000
```

---

## 📋 阶段二实战作业

1. 成功在本地电脑使用 `uv` 初始化一个 Python 项目并成功运行。
2. 编写一个 `FastAPI` 接口，接收前端传入的 `question`，并在服务端真正调用 OpenAI 或 DeepSeek 的 Python SDK 流式生成接口。
3. 用前端（Fetch 或 EventSource）对接本地的 Python FastAPI 接口，实现前后端彻底联调。
