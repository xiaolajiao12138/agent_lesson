# DAY 51：FastAPI 企业级工程化与核心方法全解

> **所属阶段**：phase07 后端工程化（P0 必修）  
> **配套代码**：[`phase07-backend-engineering/day51_fastapi_engineering.py`](../phase07-backend-engineering/day51_fastapi_engineering.py)  
> **学完能做什么**：彻底搞懂 FastAPI 里所有长得很像的方法（传参、响应、依赖注入、生命周期、后台任务、异常处理、路由拆分）各自的作用与区别，能把单文件 Demo 拆成真正可维护的企业级后端项目。

---

## 1. 请求传参“四大金刚”对比：`Path` vs `Query` vs `Body` vs `Header`

在写 FastAPI 接口时，你在函数括号里写的参数，FastAPI 是怎么知道该从 URL 路径取、从 `?a=1` 取、还是从 JSON 请求体取的？

### 1.1 四种传参方式全方位对比表

| 方法 / 写法 | 数据从哪来 | 前端怎么传 | 典型场景 | 区别与注意事项 |
| :--- | :--- | :--- | :--- | :--- |
| **`Path(...)`** | URL 路径中的 `{占位符}` | `fetch('/api/sessions/sess_123')` | 定位某一个具体资源（会话 ID、用户 ID、文档 ID） | 路径里写了 `{session_id}`，函数参数名就必须叫 `session_id`；**永远是必填的**（不能设 `default=None`） |
| **`Query(...)`** | URL 问号后面的 `?key=val` | `fetch('/api/sessions?page=1&size=20')` | 分页、搜索关键词、过滤条件、排序 | 函数的**基础类型参数**（`str`/`int`/`bool`）如果不出现在路径里，**默认就是 `Query`** |
| **`BaseModel` 子类 / `Body(...)`** | HTTP 请求体（JSON Body） | `fetch(url, { method: 'POST', body: JSON.stringify({...}) })` | 聊天消息、创建工单、复杂表单提交 | 只要参数类型继承自 Pydantic `BaseModel`，FastAPI **自动把它当成 JSON Body 解析**；`GET` 请求不能有 Body |
| **`Header(...)`** | HTTP 请求头（Headers） | `fetch(url, { headers: { 'X-Api-Key': 'xxx' } })` | Token 鉴权、追踪 ID（`X-Request-Id`）、租户 ID | Python 变量名用下划线 `x_api_key`，FastAPI 会**自动把 `-` 转成 `_`** 去匹配请求头 `X-Api-Key`（默认 `convert_underscores=True`） |
| **`Form(...)` / `File(...)` / `UploadFile`** | `multipart/form-data` 表单 | `const fd = new FormData(); fd.append('file', file)` | RAG 上传 PDF / Word / 图片文件 | 上传文件**必须用 `UploadFile`**，不能和 JSON `BaseModel` 写在同一个接口里（因为 `Content-Type` 不同） |

### 1.2 一眼看懂：同一个接口同时接收 4 种参数

```python
from fastapi import FastAPI, Path, Query, Body, Header
from pydantic import BaseModel

class ChatMessage(BaseModel):
    query: str
    temperature: float = 0.7

@app.post("/api/v1/sessions/{session_id}/chat")
async def chat(
    # 1. Path：来自 URL 里的 {session_id}
    session_id: str = Path(..., min_length=3, description="会话ID"),
    # 2. Query：来自 URL 问号后的 ?stream=true
    stream: bool = Query(default=False, description="是否开启流式输出"),
    # 3. Body：来自 POST 的 JSON 请求体
    payload: ChatMessage = Body(..., description="聊天请求体"),
    # 4. Header：来自请求头 X-Trace-Id（自动把 _ 映射为 -）
    x_trace_id: str | None = Header(default=None, description="链路追踪ID"),
):
    ...
```

### 1.3 单个简单值想放进 JSON Body 怎么办？（`Body(embed=True)`）

如果你不想专门写一个 `class Xxx(BaseModel)`，只想让前端传 `{"bio": "大家好..."}`：
- **不加 `Body`**（写 `bio: str`）➡️ FastAPI 默认当成 **URL 问号参数 `?bio=xxx`**（这就是你之前遇到 `422` 错误的原因！）；
- **加 `Body(..., embed=True)`** ➡️ FastAPI 会从 JSON 请求体 `{"bio": "xxx"}` 中读取 `bio` 字段！

---

## 2. 响应返回“五大金刚”对比：什么时候直接 `return`，什么时候包一层 `Response`？

| 返回方式 | Content-Type | 作用 | 是否支持 `response_model` | 什么时候用 |
| :--- | :--- | :--- | :---: | :--- |
| **直接 `return 对象/字典`** | `application/json` | FastAPI 自动用 Pydantic 校验并转成 JSON | ✅ 支持（且推荐） | **90% 的常规接口**（查列表、一次性返回结构化卡片） |
| **`JSONResponse(content=..., status_code=..., headers=...)`** | `application/json` | 手动指定 HTTP 状态码、自定义响应头 | ❌ 跳过 `response_model` | 在全局异常处理器里自定义报错状态码（如 401/500），或需要加特殊响应头时 |
| **`StreamingResponse(gen, media_type="text/event-stream")`** | 你指定的 `media_type` | 把生成器 `yield` 出来的字符/字节一块块推给前端 | ❌ 不能加 `response_model` | **Agent 流式打字机、A2UI 分阶段推送卡片**、流式返回大文件 |
| **`EventSourceResponse(gen)`**（来自 `sse-starlette`） | `text/event-stream` | 自动帮你把 `yield {"event": "ui_card", "data": "..."}` 包装成标准 `event: ...\ndata: ...\n\n` 格式，并自动发送心跳包防断连 | ❌ 不能加 `response_model` | 比手拼 `f"event: xxx\ndata: ...\n\n"` 的 `StreamingResponse` 更省心、不容易写错换行符 |
| **`FileResponse(path, filename=...)`** | 自动根据后缀识别 | 让浏览器直接下载或预览本地文件（如导出的 PDF 报告、Excel） | ❌ | Agent 生成完 Word / PDF 报告后提供下载链接 |

> [!WARNING]
> **避坑复习**：`StreamingResponse` 和 `response_model=Xxx` **绝对不能同时出现在同一个接口上**！因为 `response_model` 要求一次性拿到完整对象做校验，而 `StreamingResponse` 返回的是一个还没开始跑的流生成器。

---

## 3. 路由组织对比：`@app.get` vs `APIRouter`（单文件 vs 企业级多文件分层）

| 写法 | 适用规模 | 作用与区别 |
| :--- | :--- | :--- |
| `@app.get("/api/chat")` | 单文件练习 Demo（< 200 行） | 所有接口全堆在 `main.py` 里，超过 10 个接口就乱成一锅粥 |
| **`APIRouter(prefix="/api/v1/chat", tags=["对话"])`** + **`app.include_router(router)`** | ✅ **真实项目标配** | 对标前端 Express 的 `express.Router()` 或 Vue Router 的模块化路由：每个业务模块（用户、会话、知识库、Agent）各自一个文件，最后在 `main.py` 里用 `app.include_router()` 汇总挂载 |

**企业级 FastAPI 标准目录结构（直接照抄这套模板建项目）**：
```text
my_agent_backend/
├── app/
│   ├── main.py              # 入口：创建 FastAPI 实例、挂载 CORS、汇总 include_router
│   ├── config.py            # 配置：pydantic-settings 读取 .env
│   ├── dependencies.py      # 公共依赖：Depends 获取当前登录用户、数据库会话
│   ├── schemas/             # Pydantic 模型层（出入参数据结构，类似 TS 的 types/）
│   │   ├── chat.py
│   │   └── knowledge.py
│   ├── routers/             # 路由层（只管接请求和返响应，类似 Controller）
│   │   ├── chat.py          # APIRouter(prefix="/api/v1/chat")
│   │   └── knowledge.py     # APIRouter(prefix="/api/v1/kb")
│   └── services/            # 核心业务逻辑层（LangGraph 编排、RAG 检索）
│       ├── agent_service.py
│       └── rag_service.py
├── .env
└── pyproject.toml
```

---

## 4. 依赖注入 `Depends` 全解（FastAPI 最强核心机制）

很多前端同学刚看 FastAPI 时会困惑：**“为什么不直接在函数里调 `user = get_current_user(token)`，非要写成 `user = Depends(get_current_user)`？”**

### 4.1 普通函数调用 vs `Depends` 的 4 大核心区别

| 对比维度 | 在接口里直接调普通函数 `get_user()` | 使用 `Depends(get_user)` |
| :--- | :--- | :--- |
| **1. 自动提取请求参数** | ❌ 你得自己在接口上声明 `token: str = Header(...)` 再手动传进去 | ✅ `get_user` 自己声明需要什么 Header/Query，FastAPI 自动从请求里提取喂给它，接口函数干干净净 |
| **2. 自动生成 Swagger 文档锁图标** | ❌ 文档不知道这个接口需要登录 | ✅ `/docs` 页面自动显示小锁图标，支持一键填入 Token 测试所有接口 |
| **3. 支持 `yield` 自动收尾（资源释放）** | ❌ 如果接口中途报错，后面的 `db.close()` 容易漏执行 | ✅ **支持带 `yield` 的依赖**：`yield` 之前的代码在接口执行前跑，`yield` 之后的代码在接口返回后（哪怕报错了）**100% 自动执行**（用于关闭数据库 Session） |
| **4. 单元测试一键替换（Mock）** | ❌ 写死在函数内部，测试时很难替换 | ✅ 测试时只需一行 `app.dependency_overrides[get_user] = mock_user` 就能替换掉鉴权或数据库 |

### 4.2 带 `return` 的依赖 vs 带 `yield` 的依赖

```python
# ① 带 return 的依赖：适合“只管拿东西，不需要清理”（如检查 Token、读取配置）
async def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != "secret-key":
        raise HTTPException(status_code=401, detail="无效的 API Key")
    return x_api_key

# ② 带 yield 的依赖：适合“用完必须关门”（如数据库连接、临时文件）
async def get_db_session():
    print("1. [进入接口前] 打开数据库会话")
    session = {"db": "connected"}
    try:
        yield session          # 👈 把 session 注入给接口函数使用
    finally:
        print("3. [接口结束后] 自动关闭数据库会话，绝不泄漏连接！")
```

### 4.3 `Depends` 放在 3 个不同位置的区别

| 挂载位置 | 写法 | 生效范围 | 能否拿到返回值 |
| :--- | :--- | :--- | :---: |
| **接口函数参数里** | `def chat(user = Depends(get_user)):` | 仅当前这 1 个接口 | ✅ 能（通过参数 `user` 拿到） |
| **`APIRouter` 上** | `APIRouter(dependencies=[Depends(verify_key)])` | 该路由文件下的**所有接口** | ❌ 只做拦截安检，不拿返回值 |
| **`FastAPI(app)` 上** | `FastAPI(dependencies=[Depends(log_request)])` | 整个项目的**全部接口** | ❌ 只做全局拦截 |

---

## 5. 应用生命周期：`lifespan` vs `@app.on_event("startup")`

当服务启动时，我们需要**提前初始化好 `AsyncOpenAI` 客户端、数据库连接池、Chroma 向量库**（而不是每次用户发请求都重新 `new` 一个客户端，那样又慢又浪费连接）。

| 写法 | 状态 | 区别 |
| :--- | :--- | :--- |
| **`lifespan`（`@asynccontextmanager`）** | ✅ **现代唯一标准写法** | 用一个 `yield` 把“启动逻辑”和“关闭逻辑”写在同一个函数里，还能共享局部变量，挂到 `app.state` 上供全局使用 |
| `@app.on_event("startup")` / `("shutdown")` | ❌ **官方已标记废弃（Deprecated）** | 启动和关闭拆成两个函数，没法直接用 `try/finally` 共享变量，新代码不要再用 |

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from openai import AsyncOpenAI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== 🚀 yield 之前：服务启动时只执行 1 次 =====
    print("服务启动：正在初始化全局 AsyncOpenAI 客户端与向量库连接...")
    app.state.llm_client = AsyncOpenAI(api_key="...", base_url="...")
    
    yield  # 👈 服务正常运行期间停在这里
    
    # ===== 🛑 yield 之后：服务按 Ctrl+C 关闭时自动执行 =====
    print("服务关闭：正在安全释放连接池...")
    await app.state.llm_client.close()

app = FastAPI(lifespan=lifespan)
```

---

## 6. 后台任务对比：`BackgroundTasks` vs `asyncio.create_task` vs `Celery`

场景：用户上传了一份 50 页的 PDF 到知识库，解析 + 切分 + 算 Embedding 需要 20 秒。你不能让前端请求干等 20 秒，而是应该**立刻返回 `{"status": "处理中", "doc_id": "123"}`**，然后去后台慢慢解析。

| 方案 | 怎么用 | 优点 | 缺点 | 什么时候用 |
| :--- | :--- | :--- | :--- | :--- |
| **`BackgroundTasks`**（FastAPI 内置） | 在接口参数里声明 `bg: BackgroundTasks`，调用 `bg.add_task(func, arg1)` | 零额外依赖；支持同步函数（自动进线程池）和异步函数；在响应发给前端后立刻执行 | 和 FastAPI 在同一个进程里；如果服务重启，还没跑完的任务就丢了 | ✅ **中小型项目首选**：写审计日志、发通知邮件、轻量级文档入库 |
| `asyncio.create_task(coro)` | 直接在 `async def` 里调 | 立刻并发开始跑（不等响应返回才开始） | 如果不保存 task 引用，可能被垃圾回收；异常没人捕获会静默丢失 | 在同一个请求内部并发跑支线任务 |
| `Celery` / `ARQ` + Redis | 独立启动 Worker 进程，通过 Redis 队列派发任务 | 服务重启不丢任务；支持失败重试、定时任务、多机器分布式 | 需要额外部署 Redis 和 Worker 进程，架构重 | 大型生产系统：几百 MB 的视频/大批量 PDF 解析 |

---

## 7. 异常处理对比：`HTTPException` vs `@app.exception_handler`

| 方式 | 作用 | 默认返回格式 | 典型用法 |
| :--- | :--- | :--- | :--- |
| **`raise HTTPException(status_code=404, detail="会话不存在")`** | 在任意业务代码或 `Depends` 里立刻中断请求并返回指定错误码 | `{"detail": "会话不存在"}` | 单个地方快速抛错（类似 JS `throw new Error()`） |
| **`@app.exception_handler(自定义异常类)`** | **全局异常拦截器**：整个项目里只要抛出该异常，统一由这里接管并返回规范格式 | 由你完全自定义（如前端最爱的 `{"code": 40001, "msg": "...", "data": null}`） | ✅ 企业级项目统一错误码、拦截大模型限流错误 (`RateLimitError`) 并转成友好的前端提示 |
| `@app.exception_handler(RequestValidationError)` | 覆盖 FastAPI 默认的 **`422` 参数校验报错格式** | 可把英文的 422 报错翻译成干净的中文提示返给前端 | 前端不想看到一大坨复杂的 422 数组时使用 |
