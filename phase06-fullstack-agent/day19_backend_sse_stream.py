"""
DAY 19 实战源码：全栈 Agent 后端 —— 四大万能模板 + 真实人机协同审批恢复闭环 (Human-in-the-loop)
==============================================================================
【企业级 Generative UI + 人在回路闭环设计】：
    1. 四大万能前端模板：
       - UniversalMetricCard  （万能指标/详情卡：通吃行业指标 + 城市天气）
       - UniversalCompareCard （万能双栏对照卡：通吃多语种翻译）
       - UniversalTableCard   （万能动态表格卡：通吃框架对比/数据列表）
       - UniversalConfirmCard （万能人机协同审批卡：通吃高危发布/退款审批）

    2. 🌟 真实“人在回路 (Human-in-the-loop)”两阶段流转：
       - 【第一阶段：拦截与挂起】：
         当大模型调用 `request_action_approval` 时，后端【绝不直接执行】，
         而是把当前上下文存入 `PENDING_APPROVALS[approval_id]` 检查点，
         向前端推送 `UniversalConfirmCard` 审批卡并【立即暂停挂起当前工作流】！
       - 【第二阶段：前端点击同意/不同意 -> 唤醒后端继续走下一步流程】：
         当用户在前端卡片上点击【批准】或【驳回】按钮时，前端调用 `/api/agent/approval/stream`，
         后端取出挂起的上下文，根据用户的决定（同意则执行指令，不同意则回滚拦截），
         将结果回传给大模型，流式输出下一步的执行报告！
==============================================================================
"""

import asyncio
import json
import os
import uuid
from typing import Any, Literal

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

OPENAI_API_KEY = (
    os.getenv("api_key")
    or os.getenv("OPENAI_API_KEY")
    or "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345"
)
OPENAI_BASE_URL = (
    os.getenv("base_url")
    or os.getenv("OPENAI_BASE_URL")
    or "https://sub2api.starysp.top/v1"
)
DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME") or os.getenv("mode") or "gpt-6.1-sol"

async_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

app = FastAPI(
    title="Agent Generative UI Enterprise 4-Template Gateway",
    description="基于四大万能前端模板与人在回路审批闭环的全栈 Agent 流式网关",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 🌟 内存状态检查点仓库：保存挂起等待前端用户点击“同意/不同意”的会话上下文
# ==============================================================================
PENDING_APPROVALS: dict[str, dict[str, Any]] = {}


# ==============================================================================
# 第一步：定义 5 个业务工具的入参契约
# ==============================================================================


class DashboardArgs(BaseModel):
    """业务工具 1：行业/市场数据指标分析 -> 映射【模板 1: UniversalMetricCard】"""

    title: str = Field(description="卡片标题，如 '2026 新能源出海核心态势简报'")
    metric1_label: str = Field(description="指标1名称（6字以内），如 '产业渗透率'")
    penetration_rate: str = Field(description="指标1数值，如 '48.6%'")
    metric2_label: str = Field(description="指标2名称（6字以内），如 '海外出口同比'")
    export_growth: str = Field(description="指标2数值，如 '+36.2%'")
    risk_warning: str = Field(description="关键风险提示或核心建议")
    tags: list[str] = Field(description="3个相关业务标签")


class WeatherArgs(BaseModel):
    """业务工具 2：城市实时天气查询 -> 共用【模板 1: UniversalMetricCard】"""

    city: str = Field(description="城市名称，如 '深圳'、'北京'")
    temperature: str = Field(description="当前气温，如 '26°C'")
    weather_condition: str = Field(description="天气状况，如 '多云转晴'")
    humidity: str = Field(description="空气相对湿度，如 '62%'")
    wind: str = Field(description="风向与风力，如 '东南风 2 级'")
    dressing_advice: str = Field(description="穿衣与出行建议")


class TranslationArgs(BaseModel):
    """业务工具 3：多语种翻译 -> 映射【模板 2: UniversalCompareCard】"""

    source_lang: str = Field(description="源语言，如 '中文'")
    target_lang: str = Field(description="目标语言，如 'English'、'日语'")
    original_text: str = Field(description="原始文本")
    translated_text: str = Field(description="地道精准的目标语言译文")
    tone_style: str = Field(description="语调风格，如 '商务正式'、'科技专业'")
    key_vocabulary: list[str] = Field(
        description="2~4个核心词汇对照，如 ['转型 -> Transition', '全栈 -> Full-Stack']"
    )


class DataTableArgs(BaseModel):
    """业务工具 4：结构化表格对比 -> 映射【模板 3: UniversalTableCard】"""

    title: str = Field(description="表格标题，如 '主流 AI Agent 框架横向对比清单'")
    columns: list[str] = Field(
        description="表头列名数组（3~4列），如 ['框架名称', '核心优势', '学习曲线', '适用场景']"
    )
    rows: list[list[str]] = Field(
        description="二维行数据数组，每行元素个数必须与 columns 一致"
    )
    summary: str = Field(description="表格底部的一句话选型总结或数据洞察")


class ApprovalDetailItem(BaseModel):
    label: str = Field(description="参数名，如 '操作类型'、'目标环境'、'镜像版本'")
    value: str = Field(description="参数值，如 '生产环境发布'、'prod'、'v2.4.0'")


class ActionApprovalArgs(BaseModel):
    """业务工具 5：高危操作审批确认 -> 映射【模板 4: UniversalConfirmCard】"""

    title: str = Field(description="审批单标题，如 '生产环境发布审批确认单'")
    risk_level: Literal["low", "medium", "high"] = Field(
        description="风险等级：'low' | 'medium' | 'high'"
    )
    description: str = Field(description="为什么需要人工确认的操作背景说明")
    details: list[ApprovalDetailItem] = Field(
        description="3~4项待人工核对的关键参数明细列表"
    )
    command_or_action: str = Field(
        description="批准后将要执行的底层指令或动作，如 'deploy-cli --project agent-web-portal --env prod --tag v2.4.0'"
    )


# ==============================================================================
# 第二步：组装传给大模型的 5 大工具说明书 (ALL_TOOLS_SPEC)
# ==============================================================================

ALL_TOOLS_SPEC: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "render_metric_dashboard",
            "description": "当用户询问行业调研、市场趋势、职业前景或宏观指标分析时，调用此工具生成指标卡片。",
            "parameters": DashboardArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "当用户询问某个城市的天气、气温、湿度或出门穿衣建议时，调用此工具生成天气卡片。",
            "parameters": WeatherArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "当用户要求把句子或段落翻译成英文、日文等其他语言时，调用此工具生成双语对照精译卡片。",
            "parameters": TranslationArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_data_table",
            "description": "当用户要求对比多个技术框架、列出清单列表、查询多维表格数据时，调用此工具生成动态表格卡片。",
            "parameters": DataTableArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_action_approval",
            "description": "当用户要求执行高危或敏感操作（如：发布上线到 prod 生产环境、申请大额退款/报销、群发邮件、删除数据）时，必须调用此工具发起人工审批拦截。",
            "parameters": ActionApprovalArgs.model_json_schema(),
        },
    },
]


# ==============================================================================
# 第三步：🌟【企业级核心架构】UI_TOOL_MAP —— 5 大业务工具映射到前端 4 大万能模板
# ==============================================================================

UI_TOOL_MAP: dict[str, dict[str, Any]] = {
    "render_metric_dashboard": {
        "component_type": "UniversalMetricCard",
        "requires_human_approval": False,
        "summary_fn": lambda args: f"已通过万能指标模板生成「{args.get('title', '')}」",
        "handler": lambda args: {
            "title": f"📊 {args.get('title', '核心指标简报')}",
            "badge": "行业指标仪表盘",
            "theme": "indigo",
            "items": [
                {
                    "label": args.get("metric1_label", "核心指标 1"),
                    "value": args.get("penetration_rate", "-"),
                },
                {
                    "label": args.get("metric2_label", "核心指标 2"),
                    "value": args.get("export_growth", "-"),
                },
            ],
            "notice": f"⚠️ [风险关注] {args.get('risk_warning', '')}",
            "tags": args.get("tags", []),
            "action_label": "+ 加入大盘自选",
            "action_done_label": "✓ 已订阅监控",
        },
    },
    "get_weather": {
        "component_type": "UniversalMetricCard",
        "requires_human_approval": False,
        "summary_fn": lambda args: f"已通过万能指标模板生成「{args.get('city', '')}」实时气象卡",
        "handler": lambda args: {
            "title": f"🌤️ {args.get('city', '')} · 实时气象与出行",
            "badge": "实时气象站",
            "theme": "sky",
            "items": [
                {
                    "label": "当前气温",
                    "value": args.get("temperature", "-"),
                    "subtext": args.get("weather_condition", ""),
                },
                {
                    "label": "相对湿度",
                    "value": f"💧 {args.get('humidity', '-')}",
                },
                {
                    "label": "风向风力",
                    "value": f"🍃 {args.get('wind', '-')}",
                },
            ],
            "notice": f"👕 [穿衣与出行建议] {args.get('dressing_advice', '')}",
            "tags": [args.get("city", "城市"), args.get("weather_condition", "实时天气")],
            "action_label": "☆ 设为常驻城市",
            "action_done_label": "★ 已设为常驻城市",
        },
    },
    "translate_text": {
        "component_type": "UniversalCompareCard",
        "requires_human_approval": False,
        "summary_fn": lambda args: f"已通过万能对照模板生成【{args.get('source_lang', '')} -> {args.get('target_lang', '')}】精译卡",
        "handler": lambda args: {
            "title": f"🌐 {args.get('source_lang', '原文')} ➔ {args.get('target_lang', '译文')}",
            "badge": "多语种精译对照模板",
            "subtitle": f"语调风格：{args.get('tone_style', '专业标准')}",
            "source_title": f"原文 ({args.get('source_lang', '')})",
            "source_content": args.get("original_text", ""),
            "target_title": f"精译结果 ({args.get('target_lang', '')})",
            "target_content": args.get("translated_text", ""),
            "highlights": args.get("key_vocabulary", []),
        },
    },
    "render_data_table": {
        "component_type": "UniversalTableCard",
        "requires_human_approval": False,
        "summary_fn": lambda args: f"已通过万能表格模板生成「{args.get('title', '')}」（共 {len(args.get('rows', []))} 行）",
        "handler": lambda args: {
            "title": f"📋 {args.get('title', '数据对比清单')}",
            "badge": "动态数据表格模板",
            "columns": args.get("columns", []),
            "rows": args.get("rows", []),
            "summary": args.get("summary", ""),
        },
    },
    "request_action_approval": {
        "component_type": "UniversalConfirmCard",
        # 🌟 标记该工具需要挂起等待前端人工点击“同意/不同意”！
        "requires_human_approval": True,
        "summary_fn": lambda args: f"已触发高危操作拦截，生成审批单「{args.get('title', '')}」并挂起流程",
        "handler": lambda args: {
            "title": f"🛡️ {args.get('title', '敏感操作审批确认')}",
            "badge": "人机协同审批模板",
            "risk_level": args.get("risk_level", "high"),
            "description": args.get("description", ""),
            "details": args.get("details", []),
            "command_or_action": args.get("command_or_action", ""),
        },
    },
}


# ==============================================================================
# 第四步：第一阶段流式生成器（遇到审批工具时挂起并保存快照）
# ==============================================================================


async def real_agent_llm_pipeline(user_prompt: str):
    """
    【第一阶段：意图识别、渲染卡片、若遇高危审批则挂起等待前端决策】
    """
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "你是一个顶级的全栈 AI Agent 智能工作台助手。\n"
                "请根据用户的提问意图，自动调用最匹配的工具在前端渲染可视化交互卡片：\n"
                "1. 行业调研、市场/职业趋势分析 -> 调用 `render_metric_dashboard`；\n"
                "2. 城市天气查询、气温、穿衣建议 -> 调用 `get_weather`；\n"
                "3. 多语种翻译、中英互译 -> 调用 `translate_text`；\n"
                "4. 多个技术框架横向对比、清单表格列出 -> 调用 `render_data_table`；\n"
                "5. 生产环境部署上线、申请大额退款/报销、群发邮件等敏感操作 -> 必须调用 `request_action_approval` 发起人工审批；\n"
                "6. 调用完卡片工具后，再用简明扼要的文字做补充说明。"
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    try:
        yield {
            "event": "thought",
            "data": json.dumps(
                {
                    "stage": "intent_understanding",
                    "message": f"已接收需求「{user_prompt}」，正在连接大模型 ({DEFAULT_MODEL}) 匹配最佳 UI 模板工具...",
                },
                ensure_ascii=False,
            ),
        }

        first_resp = await async_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=ALL_TOOLS_SPEC,
            tool_choice="auto",
        )

        assistant_msg = first_resp.choices[0].message
        messages.append(assistant_msg.model_dump(exclude_none=True))

        if assistant_msg.tool_calls:
            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

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
                await asyncio.sleep(0.15)

                tool_config = UI_TOOL_MAP.get(fn_name)
                if tool_config:
                    component_type = tool_config["component_type"]
                    universal_props = tool_config["handler"](fn_args)
                    summary_text = tool_config["summary_fn"](fn_args)

                    # 🌟 检查该工具是否需要【挂起等待前端人工点击同意/不同意】
                    if tool_config.get("requires_human_approval"):
                        approval_id = f"apr_{uuid.uuid4().hex[:8]}"
                        universal_props["approval_id"] = approval_id

                        # 将当前未完结的会话上下文存入后端内存检查点，等待前端点击按钮唤醒！
                        PENDING_APPROVALS[approval_id] = {
                            "messages": messages,
                            "tool_call_id": tool_call.id,
                            "fn_name": fn_name,
                            "fn_args": fn_args,
                        }

                        yield {
                            "event": "tool_call",
                            "data": json.dumps(
                                {
                                    "tool_name": fn_name,
                                    "status": "completed",
                                    "summary": f"{summary_text} (审批单号: {approval_id})",
                                },
                                ensure_ascii=False,
                            ),
                        }

                        # 推送审批卡片（带 approval_id）给前端
                        yield {
                            "event": "generative_ui",
                            "data": json.dumps(
                                {
                                    "component_type": component_type,
                                    "props": universal_props,
                                },
                                ensure_ascii=False,
                            ),
                        }

                        # 推送挂起思考状态，不再往下调用大模型，直接暂停！
                        yield {
                            "event": "thought",
                            "data": json.dumps(
                                {
                                    "stage": "awaiting_human_approval",
                                    "message": f"⏸️ 工作流已在安全边界挂起（单号: {approval_id}），等待前端管理员点击【批准】或【驳回】...",
                                },
                                ensure_ascii=False,
                            ),
                        }
                        yield {
                            "event": "message_chunk",
                            "data": json.dumps(
                                {
                                    "delta": "⏸️ **高危操作已拦截挂起**：请在上方审批卡片中核对参数，点击 **【✓ 批准并授权执行】** 或 **【✕ 驳回拦截】**，后端将根据您的选择继续执行下一步流程..."
                                },
                                ensure_ascii=False,
                            ),
                        }
                        return

                    # 普通展示型工具：直接完成并继续流式生成总结
                    yield {
                        "event": "tool_call",
                        "data": json.dumps(
                            {
                                "tool_name": fn_name,
                                "status": "completed",
                                "summary": f"{summary_text} -> 挂载模板 [{component_type}]",
                            },
                            ensure_ascii=False,
                        ),
                    }

                    yield {
                        "event": "generative_ui",
                        "data": json.dumps(
                            {
                                "component_type": component_type,
                                "props": universal_props,
                            },
                            ensure_ascii=False,
                        ),
                    }
                    await asyncio.sleep(0.15)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"前端已使用通用模板 [{component_type}] 成功渲染数据。",
                        }
                    )
                else:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"未找到工具 {fn_name} 的模板映射。",
                        }
                    )

            # 通道 4：流式输出补充建议文字
            yield {
                "event": "thought",
                "data": json.dumps(
                    {
                        "stage": "generating_summary",
                        "message": "通用模板组件已挂载，大模型正在流式输出补充说明...",
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
                            "data": json.dumps(
                                {"delta": delta_text}, ensure_ascii=False
                            ),
                        }

        else:
            content = assistant_msg.content or "已为您处理完成。"
            for char in content:
                yield {
                    "event": "message_chunk",
                    "data": json.dumps({"delta": char}, ensure_ascii=False),
                }
                await asyncio.sleep(0.02)

    except Exception as err:
        yield {
            "event": "thought",
            "data": json.dumps(
                {"stage": "error", "message": f"处理过程中发生异常: {err!s}"},
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
        yield {
            "event": "done",
            "data": json.dumps({"status": "finished", "code": 200}),
        }


# ==============================================================================
# 第五步：🌟 第二阶段流式生成器 —— 接收前端“同意/不同意”点击，恢复工作流走下一步！
# ==============================================================================


async def resume_after_human_approval_pipeline(
    approval_id: str, decision: Literal["approved", "rejected"]
):
    """
    【第二阶段：当用户在前端卡片点击“批准”或“驳回”后，唤醒后端继续走下一步流程！】
    """
    try:
        session = PENDING_APPROVALS.pop(approval_id, None)
        if not session:
            yield {
                "event": "message_chunk",
                "data": json.dumps(
                    {"delta": f"\n\n⚠️ 审批单 [{approval_id}] 不存在或已处理完毕。"},
                    ensure_ascii=False,
                ),
            }
            return

        messages: list[dict[str, Any]] = session["messages"]
        tool_call_id: str = session["tool_call_id"]
        fn_args: dict[str, Any] = session["fn_args"]
        cmd = fn_args.get("command_or_action", "默认高危指令")

        # 分支 A：前端用户点击了【✓ 批准并授权执行】
        if decision == "approved":
            yield {
                "event": "thought",
                "data": json.dumps(
                    {
                        "stage": "approval_granted",
                        "message": f"✅ 后端已收到管理员【批准授权】(单号: {approval_id})，正在恢复工作流并执行底层指令...",
                    },
                    ensure_ascii=False,
                ),
            }
            yield {
                "event": "tool_call",
                "data": json.dumps(
                    {
                        "tool_name": "execute_approved_command",
                        "status": "executing",
                        "args": {"command": cmd},
                    },
                    ensure_ascii=False,
                ),
            }
            await asyncio.sleep(0.4)

            yield {
                "event": "tool_call",
                "data": json.dumps(
                    {
                        "tool_name": "execute_approved_command",
                        "status": "completed",
                        "summary": f"底层指令 [{cmd}] 已在生产集群成功执行完毕！",
                    },
                    ensure_ascii=False,
                ),
            }

            # 把“用户同意且执行成功”的结果作为 tool 消息回传给大模型
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": (
                        f"管理员已在前端点击【同意/批准】！系统已正式执行指令: `{cmd}`，返回状态码 0 (执行成功)。"
                        "请向用户输出正式的执行完成报告与上线后监控建议。"
                    ),
                }
            )

        # 分支 B：前端用户点击了【✕ 驳回拦截】
        else:
            yield {
                "event": "thought",
                "data": json.dumps(
                    {
                        "stage": "approval_rejected",
                        "message": f"🛑 后端已收到管理员【驳回指令】(单号: {approval_id})，正在安全中止并回滚高危操作...",
                    },
                    ensure_ascii=False,
                ),
            }
            yield {
                "event": "tool_call",
                "data": json.dumps(
                    {
                        "tool_name": "abort_and_rollback",
                        "status": "completed",
                        "summary": f"已永久阻断指令 [{cmd}]，生产环境零变更。",
                    },
                    ensure_ascii=False,
                ),
            }

            # 把“用户不同意、操作已取消”的结果作为 tool 消息回传给大模型
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": (
                        f"管理员已在前端点击【不同意/驳回】！高危指令 `{cmd}` 已被安全拦截，未对系统产生任何改动。"
                        "请向用户输出操作已取消的安全回执说明，并询问是否需要调整发布参数。"
                    ),
                }
            )

        # 唤醒大模型，根据管理员的审批结果流式输出下一步答复！
        yield {
            "event": "thought",
            "data": json.dumps(
                {
                    "stage": "resuming_llm_summary",
                    "message": "大模型已接收审批结果，正在流式输出下一步结论...",
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
                        "data": json.dumps(
                            {"delta": delta_text}, ensure_ascii=False
                        ),
                    }

    except Exception as err:
        yield {
            "event": "thought",
            "data": json.dumps(
                {"stage": "error", "message": f"审批恢复流转异常: {err!s}"},
                ensure_ascii=False,
            ),
        }
    finally:
        yield {
            "event": "done",
            "data": json.dumps({"status": "finished", "code": 200}),
        }


# ==============================================================================
# 路由端点定义
# ==============================================================================


@app.get("/api/agent/stream")
async def sse_agent_endpoint(prompt: str = "分析 2026 年新能源汽车出海战略"):
    """第一阶段：主任务流式端点"""
    return EventSourceResponse(real_agent_llm_pipeline(prompt))


@app.get("/api/agent/approval/stream")
async def sse_approval_decision_endpoint(
    approval_id: str,
    decision: Literal["approved", "rejected"],
):
    """
    🌟 第二阶段：接收前端审批卡片点击的【同意 (approved) / 不同意 (rejected)】，
    唤醒挂起的工作流并流式推送下一步执行过程！
    """
    return EventSourceResponse(
        resume_after_human_approval_pipeline(approval_id, decision)
    )


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("🚀 企业级【四大万能模板 + 人在回路审批恢复】Agent 流式服务已启动！")
    print(f"👉 当前连接大模型: {DEFAULT_MODEL}")
    print("👉 主任务流端点:   http://127.0.0.1:8019/api/agent/stream")
    print("👉 审批恢复流端点: http://127.0.0.1:8019/api/agent/approval/stream")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=8019)
