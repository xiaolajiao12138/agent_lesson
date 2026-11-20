import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionToolParam
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(parent_dir, ".env"), override=True)
load_dotenv(os.path.join(current_dir, ".env"), override=True)
OPENAI_API_KEY = os.getenv("api_key")
OPENAI_BASE_URL = os.getenv("base_url")
DEFAULT_MODEL = os.getenv("mode")
app = FastAPI(
    title="Agent Generative UI streaming Gateway",
    description="提供全栈Agent结构化多通道流式推送服务网关",
)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DashboardArgs(BaseModel):
    title: str = Field(
        description="卡片标题，根据用户提出问题动态生成，例如：2026 AI Agent就业市场简报"
    )
    metric1_label: str = Field(
        description="第一个核心指标的名称（6字以内），根据提问主题动态命名，如 '岗位需求涨幅'、'产业渗透率'"
    )
    penetration_rate: str = Field(
        description="第一个核心指标的具体数值，例如：'+65.0%' 或 '48.6%'"
    )
    metric2_label: str = Field(
        description="第二个核心指标的名称（6字以内），根据提问主题动态命名，如 '平均薪资溢价'、'海外出口同比'"
    )
    export_growth: str = Field(
        description="第二个核心指标的具体数值，例如：'+35.2%' 或 '25k-45k'"
    )
    risk_warning: str = Field(description="针对该主题的关键风险提示、挑战或核心建议")
    tags: list[str] = Field(description="3个与用户提问主题紧密相关的标签")


class WeatherArgs(BaseModel):
    """天气卡片的字段契约。这里由模型填写，接入天气 API 后才能用于实时天气查询。"""

    city: str = Field(description="城市名称，如 '深圳'")
    temperature: str = Field(description="当前气温，如 '26°C'")
    weather: str = Field(description="天气状况，如 '多云转晴'")
    advice: str = Field(description="穿衣与出行建议")
    date: str = Field(default="当日", description="日期，如2026-12-30")


# ==============================================================================
# 🌟 核心企业级 Map：后端工具名 -> 前端 React 组件名 & 数据处理函数
# ==============================================================================
UI_TOOL_MAP = {
    "render_metric_dashboard": {
        "component_type": "MetricDashboardCard",  # 对应前端的指标卡组件
        "handler": lambda args: args,  # 直接把大模型生成的字段传给前端
    },
    "get_weather": {
        "component_type": "WeatherForecastCard",  # 对应前端的天气卡组件
        "handler": lambda args: {  # 也可以在后端补充/加工字段再传给前端
            **args,
            "update_time": "刚刚更新",
        },
    },
}
# 工具
DASHBOARD_TOOL_SPEC: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "render_metric_dashboard",
            "description": (
                "当用户询问关于行业调研、市场趋势、数据分析、技术方案或商业规划时，"
                "必须调用此工具生成一个包含核心数据指标与风险分析的交互式卡片展示给前端用户。"
            ),
            "parameters": DashboardArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "当用户询问关于指定城市天气，气温时，"
                "必须调用此工具生成一个包含核心数据指标的交互式卡片展示给前端用户。"
            ),
            "parameters": WeatherArgs.model_json_schema(),
        },
    },
]


async def real_agent_llm_pipeline(user_prompt: str):
    """
    大模型驱动多通道流式生成器
    """
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个顶级的AI agent架构顾问"
                "当用户提出具体查询指定城市天气，行业分析，技术演讲或项目规划需求时："
                "请优先调用适合的工具，为前端生成直观的数据卡片。"
                "随后在文字中给出专业，深刻且落地的系统化建议"
            ),
        },
        # Day 19｜把调用者的问题加入 user 消息，模型才能根据本次提问选择工具。
        {"role": "user", "content": user_prompt},
    ]
    try:
        yield {
            "event": "thought",
            "data": json.dumps(
                {
                    "stage": "intent_understanding",
                    "message": f"已接受用户需求【{user_prompt}】,正在连接大模型（{DEFAULT_MODEL}）规划执行",
                },
                ensure_ascii=False,
            ),
        }
        response = await async_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=DASHBOARD_TOOL_SPEC,
            tool_choice="auto",
        )
        assistan_msg = response.choices[0].message
        messages.append(assistan_msg.model_dump(exclude_none=True))
        if assistan_msg.tool_calls:
            for tool_call in assistan_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args_raw = tool_call.function.arguments
                fn_args = json.loads(fn_args_raw)
                tool_config = UI_TOOL_MAP.get(fn_name)
                if tool_config:
                    component_type = tool_config["component_type"]
                    card_props = tool_config["handler"](fn_args)
                    ui_payload = {"component_type": component_type, "props": card_props}
                    yield {
                        "event": "generative_ui",
                        "data": json.dumps(ui_payload, ensure_ascii=False),
                    }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"已生成供前端渲染的组件【{component_type}】,数据为【{json.dumps(card_props, ensure_ascii=False)}】",
                        }
                    )

            yield {
                "event": "thought",
                "data": json.dumps(
                    {
                        "stage": "generating_summary",
                        "message": "大模型正在根据本次问题流式生成答复",
                    },
                    ensure_ascii=False,
                ),
            }
            stream_response = await async_client.chat.completions.create(
                model=DEFAULT_MODEL, messages=messages, stream=True
            )
            async for chunk in stream_response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta_text = chunk.choices[0].delta.content or ""
                    if delta_text:
                        yield {
                            "event": "message_chunk",
                            "data": json.dumps(
                                {"delta": delta_text}, ensure_ascii=False
                            ),
                        }
        else:
            content = assistan_msg.content or "已为您处理完成"
            for char in content:
                yield {
                    "event": "message_chunk",
                    "data": json.dumps({"delta": char}, ensure_ascii=False),
                }
    except Exception as e:
        print(e)
        yield {
            "event": "thought",
            "data": json.dumps(
                {"stage": "error", "message": f"处理过程中发生异常：{e}"},
                ensure_ascii=False,
            ),
        }
    finally:
        yield {"event": "done", "data": json.dumps({"status": "finished", "code": 200})}


# Day 19｜@ 将函数注册为 FastAPI 路由，缺少 @ 时接口不会出现在 /docs 中。
@app.get("/api/agent/stream")
async def sse_agent_endpoint(prompt: str = "深圳今天天气怎么样"):
    """
    SSE 流式服务接口端点。
    prompt 是未传查询参数时的默认值，URL 中的 ?prompt=... 会覆盖它。
    """
    return EventSourceResponse(real_agent_llm_pipeline(prompt))


if __name__ == "__main__":
    import uvicorn

    # 打印地址与实际监听地址共用变量，避免点进另一份练习的旧服务。
    server_host = "127.0.0.3"
    server_port = 8020
    print(f"👉 SSE 接口: http://{server_host}:{server_port}/api/agent/stream")
    print(f"👉 接口调试: http://{server_host}:{server_port}/docs")
    uvicorn.run(app, host=server_host, port=server_port)
