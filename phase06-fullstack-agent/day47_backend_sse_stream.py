"""
DAY 47 实战源码：全栈 Agent 后端 —— FastAPI 结构化 SSE 流式事件推送
==============================================================================
【文件导读】：
    智能体与普通聊天机器人的本质区别在于：
    - 普通问答只要 1~2 秒就完成了；
    - 复杂的自主 Agent 需要经历“拆解意图 -> 检索多维数据 -> 触发外部工具 -> 错误重试 -> 整合输出”，
      耗时往往长达几秒到几十秒！如果采用传统的 HTTP POST 一次性等待返回，前端用户只能干瞪眼。

    因此，现代企业级 Agent 的工业标准交互范式是【SSE (Server-Sent Events) 多事件流式推送】：
    通过在单个长连接中下发不同事件类型的帧（Event Frames）：
    1. event: "thought"       -> 思考链 (Chain-of-Thought)，前端渲染为思考动画/折叠框；
    2. event: "tool_call"     -> 工具调用状态，前端显示调用中/调用成功；
    3. event: "generative_ui" -> 结构化 UI 数据，前端根据类型动态渲染 React 交互组件！
    4. event: "message_chunk" -> 最终总结文字，逐字下发打字机流；
    5. event: "done"          -> 宣告流结束，关闭连接。

【运行要求】：
    pip install fastapi uvicorn sse-starlette
    python day47_backend_sse_stream.py
    访问测试：http://127.0.0.1:8000/api/agent/stream?prompt=分析新能源汽车
==============================================================================
"""

import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# 初始化 FastAPI 实例
app = FastAPI(
    title="Agent Generative UI Streaming Gateway",
    description="提供全栈 Agent 结构化多通道流式推送服务的网关"
)

# 开启 CORS 跨域配置，确保前端（Vite 5173 / Next.js 3000）联调畅通无阻
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def simulate_complex_agent_pipeline(user_prompt: str):
    """
    【异步多通道事件生成器 (Async Event Generator)】
    核心：使用 Python 原生异步生成器语法 (async def + yield) 依次产生事件帧。
    每个事件字典包含：
      - event: 前端在 addEventListener(event_type, ...) 时监听的事件名称
      - data: 传递给前端的 JSON 字符串载荷
    """
    # ==========================================================================
    # 通道 1：推送思考过程 (Thinking / Chain-of-Thought)
    # ==========================================================================
    # 前端监听到 'thought' 事件，将信息追加进“AI 正在思考...”的手风琴展开框中
    yield {
        "event": "thought",
        "data": json.dumps({
            "stage": "intent_understanding",
            "message": f"正在拆解用户目标「{user_prompt}」，检索行业宏观大盘数据..."
        }, ensure_ascii=False)
    }
    await asyncio.sleep(0.8) # 模拟 Agent 规划耗时

    # ==========================================================================
    # 通道 2：推送外部工具调度事件 (Tool Execution Event)
    # ==========================================================================
    # 2.1 推送工具正在调用的状态
    yield {
        "event": "tool_call",
        "data": json.dumps({
            "tool_name": "fetch_industry_report",
            "status": "executing",
            "args": {"sector": "EV_Auto", "year": "2026"}
        }, ensure_ascii=False)
    }
    await asyncio.sleep(1.2) # 模拟执行网络工具耗时

    # 2.2 推送工具执行完毕与返回摘要
    yield {
        "event": "tool_call",
        "data": json.dumps({
            "tool_name": "fetch_industry_report",
            "status": "completed",
            "summary": "成功从行业数据库拉取最新渗透率与出海出口量指标。"
        }, ensure_ascii=False)
    }
    await asyncio.sleep(0.5)

    # ==========================================================================
    # 通道 3：【核心亮点】推送 Generative UI 结构化交互卡片数据
    # ==========================================================================
    # 前端接收到该事件后，不会渲染为枯燥的纯文本，而是直接动态实例化渲染一个 React/Vue 图表卡片！
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

    # ==========================================================================
    # 通道 4：推送最终总结建议的流式打字机字符 (Streaming Text / Markdown)
    # ==========================================================================
    # 模拟大模型 token 级别的平滑逐字吐字体验
    summary_text = (
        "综上所述，当前产业正加速由国内价格竞争向全球技术与供应链输出演进。"
        "建议企业重点布局智能化车载交互体验以及自主可控的本地化合规架构。"
    )
    for char in summary_text:
        yield {
            "event": "message_chunk",
            "data": json.dumps({"delta": char}, ensure_ascii=False)
        }
        await asyncio.sleep(0.04) # 模拟真实打字机节奏延迟

    # ==========================================================================
    # 通道 5：推送任务终结通知 (Done Event)
    # ==========================================================================
    # 告知前端整个工作流已全部推送完毕，可以关闭 loading 状态并断开 SSE
    yield {
        "event": "done",
        "data": json.dumps({"status": "finished", "code": 200})
    }

# ==============================================================================
# 路由定义与服务启动
# ==============================================================================

@app.get("/api/agent/stream")
async def sse_agent_endpoint(prompt: str = "默认分析任务"):
    """
    【SSE 流式服务接口端点】
    返回 EventSourceResponse，底层会自动设置标准响应头：
      Content-Type: text/event-stream
      Cache-Control: no-cache
      Connection: keep-alive
    """
    return EventSourceResponse(simulate_complex_agent_pipeline(prompt))

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Agent SSE 多通道流式服务已启动: http://127.0.0.1:8000")
    print("测试流式端点: http://127.0.0.1:8000/api/agent/stream?prompt=分析新能源")
    print("支持浏览器直接打开上述链接观察原始 SSE 文本帧！")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
