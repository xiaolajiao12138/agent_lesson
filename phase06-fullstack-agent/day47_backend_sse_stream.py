"""
DAY 47 实战源码：全栈 Agent 后端 —— FastAPI 结构化 SSE 流式事件推送
文件说明：
    智能体与普通聊天机器人的本质区别在于：Agent 执行时间长（几秒到几十秒），
    包含中间思考（CoT）、工具触发、中间数据卡片（Generative UI）和最终流式打字机。
    本文件演示如何通过 SSE 协议下发多事件流（EventSource）。
运行要求：
    pip install fastapi uvicorn sse-starlette
    python day47_backend_sse_stream.py
    访问测试：http://127.0.0.1:8000/api/agent/stream?prompt=分析新能源汽车
"""

import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Agent Generative UI Streaming Gateway")

# 开启跨域，确保本地前端开发服务器（如 Vite 5173 / Next.js 3000）畅通连接
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def simulate_complex_agent_pipeline(user_prompt: str):
    """
    异步事件生成器：
    依次向前端推送不同类型的事件帧，前端根据 event 字段动态执行不同动作
    """
    # -----------------------------------------------------------------------
    # 事件 1：推送思考过程 (Thinking / Chain-of-Thought)
    # -----------------------------------------------------------------------
    yield {
        "event": "thought",
        "data": json.dumps({
            "stage": "intent_understanding",
            "message": f"正在拆解用户目标「{user_prompt}」，检索行业宏观大盘数据..."
        }, ensure_ascii=False)
    }
    await asyncio.sleep(0.8)

    # -----------------------------------------------------------------------
    # 事件 2：推送外部工具调度事件 (Tool Execution Event)
    # -----------------------------------------------------------------------
    yield {
        "event": "tool_call",
        "data": json.dumps({
            "tool_name": "fetch_industry_report",
            "status": "executing",
            "args": {"sector": "EV_Auto", "year": "2026"}
        }, ensure_ascii=False)
    }
    await asyncio.sleep(1.2)

    yield {
        "event": "tool_call",
        "data": json.dumps({
            "tool_name": "fetch_industry_report",
            "status": "completed",
            "summary": "成功从数据库拉取行业最新渗透率与出海出口量指标。"
        }, ensure_ascii=False)
    }
    await asyncio.sleep(0.5)

    # -----------------------------------------------------------------------
    # 事件 3：核心亮点！推送 Generative UI 结构化交互卡片数据
    # -----------------------------------------------------------------------
    # 前端接收到该事件后，不会渲染为枯燥文本，而是渲染为一个精美的 React 卡片组件
    ui_card_payload = {
        "component_type": "MetricDashboardCard",
        "props": {
            "title": "2026 新能源出海核心态势简报",
            "penetration_rate": "48.6%",
            "export_growth": "+36.2%",
            "risk_warning": "海外特定市场存在关税变动风险，需关注本地化建厂进程",
            "tags": ["出海提速", "电池技术迭代", "智能化座舱"]
        }
    }
    yield {
        "event": "generative_ui",
        "data": json.dumps(ui_card_payload, ensure_ascii=False)
    }
    await asyncio.sleep(0.6)

    # -----------------------------------------------------------------------
    # 事件 4：推送最终总结建议的流式打字机字符 (Streaming Markdown)
    # -----------------------------------------------------------------------
    summary_text = (
        "综上所述，当前产业正加速由国内价格战向全球技术与供应链输出演进。"
        "建议企业重点布局智能化车载交互体验以及自主可控的本地化合规架构。"
    )
    for char in summary_text:
        yield {
            "event": "message_chunk",
            "data": json.dumps({"delta": char}, ensure_ascii=False)
        }
        await asyncio.sleep(0.04) # 模拟打字机间隔节奏

    # -----------------------------------------------------------------------
    # 事件 5：推送任务终结通知
    # -----------------------------------------------------------------------
    yield {
        "event": "done",
        "data": json.dumps({"status": "finished", "code": 200})
    }

@app.get("/api/agent/stream")
async def sse_agent_endpoint(prompt: str = "默认分析任务"):
    """
    SSE 接口端点：返回 EventSourceResponse
    """
    return EventSourceResponse(simulate_complex_agent_pipeline(prompt))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Agent SSE 流式服务已启动: http://127.0.0.1:8000")
    print("测试流式端点: http://127.0.0.1:8000/api/agent/stream?prompt=分析新能源")
    uvicorn.run(app, host="127.0.0.1", port=8000)
