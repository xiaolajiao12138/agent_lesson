"""
DAY 03 实战源码：FastAPI 现代异步微服务（对标 Express / Next.js API Routes）
文件说明：
    构建供前端调用的 Agent 后端服务接口，支持异步非阻塞、强类型入参校验与自动化文档。
运行方式：
    python day03_fastapi_server.py
    启动后访问浏览器地址：http://127.0.0.1:8000/docs (自动生成的 Swagger 交互式文档)
"""

import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 1. 初始化 FastAPI 实例（类似 express() 或 koa()）
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Agent 后端网关服务",
    description="提供给前端 Vue/React 调用的智能体调度与状态管理 API",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# 2. 跨域配置（CORS Middleware）
# ---------------------------------------------------------------------------
# 彻底解决前端本地开发（如 http://localhost:3000 或 5173）联调时的跨域拦截问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 允许所有前端来源，生产环境可替换为具体域名
    allow_credentials=True,         # 允许携带 Cookie/授权凭据
    allow_methods=["*"],            # 允许 GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],            # 允许自定义请求头
)

# ---------------------------------------------------------------------------
# 3. 定义请求与响应的 DTO (Data Transfer Object)
# ---------------------------------------------------------------------------

class UserQueryRequest(BaseModel):
    """前端向 Agent 发起提问的请求体"""
    session_id: str = Field(..., description="会话ID，用于串联上下文或 LangGraph 检查点")
    prompt: str = Field(..., min_length=1, max_length=1000, description="用户的提问内容")
    model_preference: str = Field(default="gpt-4o", description="首选大模型型号")

class AgentExecutionResponse(BaseModel):
    """返回给前端的标准响应结构体"""
    status: str = Field(..., description="状态码：'success' | 'error'")
    session_id: str = Field(..., description="透传会话ID")
    reasoning_steps: List[str] = Field(..., description="Agent 的思考链推导过程列表")
    final_answer: str = Field(..., description="最终生成的文本答案")
    elapsed_time_seconds: float = Field(..., description="后端处理耗时")

# ---------------------------------------------------------------------------
# 4. 路由定义 (Route Handlers)
# ---------------------------------------------------------------------------

@app.get("/")
async def health_check():
    """健康检查接口，类似前端 ping 测试"""
    return {"status": "ok", "message": "Agent 后端服务正在稳定运行中 🚀"}

@app.post(
    "/api/agent/chat",
    response_model=AgentExecutionResponse,
    summary="单次调用 Agent 推理接口",
    tags=["Agent 核心接口"]
)
async def dispatch_agent_task(payload: UserQueryRequest):
    """
    接收前端问题，模拟 Agent 进行多步思考与外部工具调用，返回结构化结果
    """
    import time
    start_time = time.time()

    print(f"收到前端请求 | 会话 ID: {payload.session_id} | 用户提问: {payload.prompt}")

    # 模拟 Agent 在后台的异步思考与工具调度
    # 模拟第一步：拆解任务
    await asyncio.sleep(0.5)
    step1 = "已识别意图：查询并汇总数据。"

    # 模拟第二步：调用外部工具
    await asyncio.sleep(0.7)
    step2 = "已调用外部搜索工具 [web_search]，获取最新资讯 3 条。"

    # 模拟第三步：大模型最终汇总
    await asyncio.sleep(0.4)
    step3 = "大模型综合评估完成，生成最终答复。"

    elapsed = round(time.time() - start_time, 2)

    return AgentExecutionResponse(
        status="success",
        session_id=payload.session_id,
        reasoning_steps=[step1, step2, step3],
        final_answer=f"针对您的提问「{payload.prompt}」，系统已成功为您检索并梳理完毕！",
        elapsed_time_seconds=elapsed
    )

if __name__ == "__main__":
    import uvicorn
    print("正在启动 FastAPI 异步服务，本地访问地址: http://127.0.0.1:8000")
    print("API 文档交互地址: http://127.0.0.1:8000/docs")
    # 生产环境中推荐命令行 uvicorn day03_fastapi_server:app --reload
    uvicorn.run(app, host="127.0.0.1", port=8000)
