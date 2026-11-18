"""
DAY 19 实战源码：全栈 Agent 后端 —— 接入真实大模型 + FastAPI 结构化 SSE 流式推送
==============================================================================
【文件导读】：
    本文件已从原先的 mock 模拟逻辑，彻底升级为【真实接入你的大模型 (OpenAI / GPT / DeepSeek)】！

    【核心实现架构】：
    1. 真实大模型意图思考与工具调用 (Tool Calling)：
       - 当用户输入任何分析类任务时，大模型主动调用 `render_metric_dashboard` 工具；
       - 后端通过 `generative_ui` 事件把大模型生成的真实指标下发给前端，动态渲染 React 卡片！
    2. 真实流式 Token 打字机下发 (stream=True)：
       - 大模型生成的深度分析与总结，通过 `message_chunk` 事件实时逐字推送到前端！
    3. 全链路 SSE 多通道事件标准规范：
       - event: "thought"       -> 真实大模型思考阶段日志
       - event: "tool_call"     -> 真实的工具调度进度
       - event: "generative_ui" -> 真实的动态组件数据 (Generative UI)
       - event: "message_chunk" -> 真实的大模型流式输出
       - event: "done"          -> 流程结束信号
==============================================================================
"""

import asyncio
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from sse_starlette.sse import EventSourceResponse

# 确保加载父级与当前目录的 .env 配置
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(parent_dir, ".env"), override=True)
load_dotenv(os.path.join(current_dir, ".env"), override=True)

OPENAI_API_KEY = (
    os.getenv("api_key")
    # or os.getenv("OPENAI_API_KEY")
    # or "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345"
)
OPENAI_BASE_URL = (
    os.getenv("base_url") or os.getenv("OPENAI_BASE_URL") or "https://sub2api.starysp.top/v1"
)
DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME") or os.getenv("mode") or "gpt-6.1-sol"

# 初始化异步 OpenAI 客户端
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# 初始化 FastAPI 应用
app = FastAPI(
    title="Agent Generative UI Streaming Gateway",
    description="提供全栈 Agent 结构化多通道流式推送服务的网关",
)

# 开启 CORS 跨域配置，确保前端（Vite 5173）跨域请求通畅
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 定义提供给大模型的 Generative UI 工具说明书 (Tool Schema)
# ==============================================================================

DASHBOARD_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "render_metric_dashboard",
        "description": (
            "当用户询问关于行业调研、市场趋势、数据分析、技术方案或商业规划时，"
            "必须调用此工具生成一个包含核心数据指标与风险分析的交互式卡片展示给前端用户。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "卡片标题，根据用户提问主题动态生成，例如：'2026 AI Agent 就业市场简报'",
                },
                "metric1_label": {
                    "type": "string",
                    "description": "第一个核心指标的名称（6字以内），根据提问主题动态命名，如 '岗位需求涨幅'、'产业渗透率'、'日活增长率'",
                },
                "penetration_rate": {
                    "type": "string",
                    "description": "第一个核心指标的具体数值，例如：'+65.0%' 或 '48.6%'",
                },
                "metric2_label": {
                    "type": "string",
                    "description": "第二个核心指标的名称（6字以内），根据提问主题动态命名，如 '平均薪资溢价'、'海外出口同比'、'转化率'",
                },
                "export_growth": {
                    "type": "string",
                    "description": "第二个核心指标的具体数值，例如：'+35.2%' 或 '25k-45k'",
                },
                "risk_warning": {
                    "type": "string",
                    "description": "针对该主题的关键风险提示、挑战或核心建议",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3个与用户提问主题紧密相关的标签",
                },
            },
            "required": [
                "title",
                "metric1_label",
                "penetration_rate",
                "metric2_label",
                "export_growth",
                "risk_warning",
                "tags",
            ],
        },
    },
}

# ==============================================================================
# 核心业务：真实大模型 Agent 异步多通道生成器
# ==============================================================================


async def real_agent_llm_pipeline(user_prompt: str):
    """
    【真实大模型驱动的多通道流式生成器】
    """
    # Day 13 / 19｜工具调用前先检查业务能力。天气请求不进入报告生成流程，
    # 但仍用同一套 SSE 事件返回说明并关闭前端连接。
    if "天气" in user_prompt or "weather" in user_prompt.casefold():
        yield {
            "event": "message_chunk",
            "data": json.dumps(
                {"delta": "这个工作台尚未接入实时天气数据，暂时无法查询当前天气。"},
                ensure_ascii=False,
            ),
        }
        yield {"event": "done", "data": json.dumps({"status": "finished", "code": 200})}
        return

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个顶级的全栈 AI Agent 架构顾问。\n"
                "当用户提出具体行业分析、技术演进或项目规划需求时：\n"
                "1. 请优先调用 render_metric_dashboard 工具为前端生成直观的指标数据卡片；\n"
                "2. 随后在文字中给出专业、深刻且落地的系统化建议。"
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    try:
        # ----------------------------------------------------------------------
        # 通道 1：推送意图理解与思考链 ('thought')
        # ----------------------------------------------------------------------
        yield {
            "event": "thought",
            "data": json.dumps(
                {
                    "stage": "intent_understanding",
                    "message": f"已接收用户需求「{user_prompt}」，正在连接大模型 ({DEFAULT_MODEL}) 规划执行...",
                },
                ensure_ascii=False,
            ),
        }

        # ----------------------------------------------------------------------
        # 第一次请求大模型：判定是否需要调用 Generative UI 工具
        # ----------------------------------------------------------------------
        first_resp = await async_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=[DASHBOARD_TOOL_SPEC],
            tool_choice="auto",
        )

        assistant_msg = first_resp.choices[0].message
        messages.append(assistant_msg.model_dump(exclude_none=True))

        # ----------------------------------------------------------------------
        # 检查大模型是否调用了 Generative UI 卡片工具
        # ----------------------------------------------------------------------
        if assistant_msg.tool_calls:
            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args_raw = tool_call.function.arguments
                fn_args = json.loads(fn_args_raw)

                # 通道 2.1：推送工具调用状态
                yield {
                    "event": "tool_call",
                    "data": json.dumps(
                        {
                            "tool_name": fn_name,
                            "status": "executing",
                            "args": fn_args,
                        },
                        ensure_ascii=False,
                    ),
                }
                await asyncio.sleep(0.4)

                # 通道 2.2：推送工具调用成功
                yield {
                    "event": "tool_call",
                    "data": json.dumps(
                        {
                            "tool_name": fn_name,
                            "status": "completed",
                            "summary": f"大模型已成功生成结构化指标卡片「{fn_args.get('title', '')}」",
                        },
                        ensure_ascii=False,
                    ),
                }

                # 通道 3：【核心 Generative UI】推送动态组件给 React 渲染
                if fn_name == "render_metric_dashboard":
                    ui_payload = {
                        "component_type": "MetricDashboardCard",
                        "props": fn_args,
                    }
                    yield {
                        "event": "generative_ui",
                        "data": json.dumps(ui_payload, ensure_ascii=False),
                    }
                    await asyncio.sleep(0.3)

                # 模拟工具执行结果回填给上下文
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "组件数据已成功在前端页面挂载并渲染完毕。",
                    }
                )

            # ------------------------------------------------------------------
            # 通道 4：真实流式请求大模型最终的深度分析建议 (stream=True)
            # ------------------------------------------------------------------
            yield {
                "event": "thought",
                "data": json.dumps(
                    {
                        "stage": "generating_summary",
                        "message": "大模型正在实时流式生成详细的战略分析与落地建议...",
                    },
                    ensure_ascii=False,
                ),
            }

            stream_response = await async_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                stream=True,
            )

            async for chunk in stream_response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta_text = chunk.choices[0].delta.content or ""
                    if delta_text:
                        yield {
                            "event": "message_chunk",
                            "data": json.dumps({"delta": delta_text}, ensure_ascii=False),
                        }

        else:
            # 如果大模型直接用文字回答（未触发工具）
            content = assistant_msg.content or "已为您处理完成。"
            for char in content:
                yield {
                    "event": "message_chunk",
                    "data": json.dumps({"delta": char}, ensure_ascii=False),
                }
                await asyncio.sleep(0.02)

    except Exception as err:
        # 异常兜底防护
        yield {
            "event": "thought",
            "data": json.dumps(
                {
                    "stage": "error",
                    "message": f"处理过程中发生异常: {err!s}",
                },
                ensure_ascii=False,
            ),
        }
        yield {
            "event": "message_chunk",
            "data": json.dumps(
                {"delta": f"\n\n[系统告警] 模型调用遇到错误: {err!s}"},
                ensure_ascii=False,
            ),
        }

    finally:
        # 通道 5：通知前端流程已结束
        yield {
            "event": "done",
            "data": json.dumps({"status": "finished", "code": 200}),
        }


# ==============================================================================
# 路由定义与服务启动
# ==============================================================================


@app.get("/api/agent/stream")
async def sse_agent_endpoint(prompt: str = "分析 2026 年新能源汽车出海战略"):
    """
    【SSE 流式服务接口端点】
    """
    return EventSourceResponse(real_agent_llm_pipeline(prompt))


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 真实大模型驱动的 Agent SSE 流式服务已就绪！")
    print(f"👉 当前连接的大模型: {DEFAULT_MODEL}")
    print(f"👉 API 接入端点: {OPENAI_BASE_URL}")
    print("👉 本地服务地址: http://127.0.0.2:8019")
    print("👉 前端联调端点: http://127.0.0.2:8019/api/agent/stream")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.2", port=8019)
