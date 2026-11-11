"""
DAY 03 实战源码：FastAPI 现代异步微服务（对标 Express / Next.js API Routes）
==============================================================================
【文件导读】：
    本文件是构建 AI Agent 后端网关的核心模板。
    在现代大模型应用架构中，前端（Vue/React）与底层复杂智能体（LangGraph/MCP/大模型）之间，
    必须有一个高性能、高并发、且强类型的 Web 网关，而 FastAPI 是目前 AI 领域的绝对首选。

【核心技术点】：
    1. 异步非阻塞架构：基于 ASGI 与 asyncio，高并发请求下不会因为大模型长耗时 I/O 阻塞线程。
    2. 强类型契约校验：结合 Pydantic BaseModel，入参自动拦截校验，不合规直接返回 422。
    3. CORS 跨域放行：解决前端本地开发联调跨域阻断。
    4. 自动生成 OpenAPI/Swagger：无需人工手写 API 文档，访问 /docs 即可交互式调试。

【运行方式】：
    python day03_fastapi_server.py
    启动后在浏览器打开：
    - 交互式接口文档：http://127.0.0.1:8000/docs
    - 备用 Redoc 文档：http://127.0.0.1:8000/redoc
==============================================================================
"""

import asyncio
import time

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==============================================================================
# 1. 初始化 FastAPI 实例（类似 Node.js 中的 const app = express()）
# ==============================================================================
# title/description/version 不仅是代码注释，它们会被 FastAPI 自动提取并渲染到 /docs 的网页 UI 顶端
app = FastAPI(
    title="AI Agent 后端网关服务",
    description="提供给前端 Vue/React 调用的智能体调度与状态管理 API",
    version="1.0.0",
)

# ==============================================================================
# 2. 跨域配置（CORS Middleware）
# ==============================================================================
# 【前端痛点解析】：
# 当你本地用 Vite 启动 Vue 项目（如 http://localhost:5173），向后端 http://127.0.0.1:8000 发起 fetch/axios 请求时，
# 浏览器的“同源策略”会进行安全拦截，并报著名的 "CORS Error: No Access-Control-Allow-Origin"。
# 通过注册 CORSMiddleware 中间件，后端在响应头中自动注入允许跨域的指令。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # 允许所有前端来源访问（生产环境建议配置为具体的域名如 ["https://myapp.com"]）
    allow_credentials=True,  # 允许前端跨域请求携带 Cookie 或 Authorization 头
    allow_methods=["*"],  # 允许所有的 HTTP 动词：GET, POST, PUT, DELETE, OPTIONS
    allow_headers=[
        "*"
    ],  # 允许前端携带任何自定义请求头（例如 x-token, Content-Type 等）
)

# ==============================================================================
# 3. 定义请求与响应的 DTO (Data Transfer Object 数据传输对象)
# ==============================================================================
# 【TS 开发者快速理解】：
# 在前端我们用 interface 定义类型，但 interface 在编译成 JS 后就彻底消失了，无法做运行时拦截。
# Pydantic 的 BaseModel 则是一把“运行时安检仪”：
# 1. 静态支持：编写代码时提供完整的字段自动补全和类型推导。
# 2. 运行时拦截：前端如果少传字段、类型错误或字段为空，FastAPI 在进入函数前就会直接返回 422 报错！


class UserQueryRequest(BaseModel):
    """
    【前端请求载荷 DTO】
    对应前端 POST 请求体: { "session_id": "xxx", "prompt": "xxx", "model_preference": "gpt-4o" }
    """

    # session_id: 用于维持对话上下文记忆或 LangGraph 的 checkpoint 检查点状态
    session_id: str = Field(
        ..., description="会话ID，用于串联上下文或 LangGraph 检查点"
    )

    # min_length=1: 强制校验用户问题不能为空白字符串
    # max_length=1000: 防止超大请求攻击后端，保护 LLM Token 预算
    prompt: str = Field(
        ..., min_length=1, max_length=1000, description="用户的提问内容"
    )

    # 默认值设定：若前端不传该字段，后端自动 fallback 降级使用 gpt-4o
    model_preference: str = Field(default="gpt-4o", description="首选大模型型号")


class AgentExecutionResponse(BaseModel):
    """
    【统一后端响应体 DTO】
    强制约束后端必须严格按照该结构返回数据，杜绝前后端因字段名不一致（如 snake_case vs camelCase）导致的撕逼
    """

    status: str = Field(..., description="业务执行状态码：'success' | 'error'")
    session_id: str = Field(..., description="原样透传会话ID，供前端做消息队列对齐")
    reasoning_steps: list[str] = Field(
        ..., description="Agent 的思考链推导过程列表（前端可渲染为可折叠手风琴面板）"
    )
    final_answer: str = Field(..., description="最终生成的文本答复")
    elapsed_time_seconds: float = Field(
        ..., description="后端处理与外部工具调用总耗时（秒）"
    )


# ==============================================================================
# 4. 路由定义 (Route Handlers)
# ==============================================================================


@app.get("/")
async def health_check():
    """
    【健康检查路由】
    作用：供运维监控、Docker 容器探针 (livenessProbe) 或前端测试后端是否存活
    """
    return {"status": "ok", "message": "Agent 后端服务正在稳定运行中 [健康]"}


@app.post(
    "/api/agent/chat",
    response_model=AgentExecutionResponse,  # 响应模型约束：FastAPI 自动按该模型过滤并校验返回值
    summary="单次调用 Agent 推理接口",
    tags=["Agent 核心接口"],
)
async def dispatch_agent_task(payload: UserQueryRequest):
    """
    【Agent 任务调度入口】
    业务流程：
      1. 自动提取前端 POST 的 JSON 并实例化为 payload 对象；
      2. 模拟 Agent 接收提问并触发内部思考循环（Planning -> Tool -> Synthesis）；
      3. 组装耗时与思考链步骤，输出标准化结构数据给前端。
    """
    start_time = time.time()
    print(f"[收到前端请求] 会话 ID: {payload.session_id} | 用户提问: {payload.prompt}")

    # --------------------------------------------------------------------------
    # 模拟真实 AI Agent 在后台的异步思考与工具调度全过程
    # 【重点说明】：此处使用 await asyncio.sleep(...) 来非阻塞模拟网络 I/O 延迟
    # 如果使用阻塞的 time.sleep()，会冻结整个 Python 线程导致其他并发请求卡死！
    # --------------------------------------------------------------------------

    # 阶段 1：意图识别与任务规划 (Reasoning / Planning)
    # Agent 思考：“用户想让我干什么？需要哪些工具？”
    await asyncio.sleep(0.5)
    step1 = "已识别意图：查询并汇总相关行业与技术数据。"

    # 阶段 2：调用外部工具 (Tool Calling)
    # Agent 决策：“调用网络搜索工具获取最新真实数据”
    await asyncio.sleep(0.7)
    step2 = "已调用外部搜索工具 [web_search]，成功检索到 3 条高置信度资讯。"

    # 阶段 3：大模型多源信息融合与最终输出 (Synthesis / LLM Generation)
    # Agent 汇集工具返回的数据，输入 LLM 生成通顺、有逻辑的回复
    await asyncio.sleep(0.4)
    step3 = "大模型综合评估与上下文融合完成，生成最终答复。"

    # 计算后端端到端总处理耗时（保留两位小数）
    elapsed = round(time.time() - start_time, 2)

    # 组装 Pydantic 响应实例并返回（FastAPI 自动转为标准 JSON 字符串下发）
    return AgentExecutionResponse(
        status="success",
        session_id=payload.session_id,
        reasoning_steps=[step1, step2, step3],
        final_answer=f"针对您的提问「{payload.prompt}」，系统已成功为您检索并梳理完毕！",
        elapsed_time_seconds=elapsed,
    )


# ==============================================================================
# 5. 服务启动引导（ASGI 服务器运行）
# ==============================================================================
# 当直接 python day03_fastapi_server.py 运行时，进入主入口启动 uvicorn
if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("正在启动 FastAPI 异步服务...")
    print("服务本地访问地址: http://127.0.0.1:8000")
    print("Swagger 交互式文档: http://127.0.0.1:8000/docs")
    print("按 Ctrl + C 可终止服务")
    print("=" * 60 + "\n")

    # 生产环境中推荐通过 CLI 启动以支持代码热重载：uvicorn day03_fastapi_server:app --reload
    uvicorn.run(app, host="127.0.0.1", port=8000)
