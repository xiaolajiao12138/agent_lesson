# 【修改 1】新增 asyncio 和 Literal，删掉了原本未使用的 indent 和会与局部变量重名的 messages
# 原本是：
#   from textwrap import indent
#   from typing import TypedDict
#   from langchain_core import messages
import asyncio
import os
import sys
from typing import Literal, TypedDict

from langgraph.types import Command

# 动态引入项目根目录的通用配置
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from config import DEFAULT_MODEL, get_async_openai_client
except ImportError:
    from openai import AsyncOpenAI

    def get_async_openai_client():
        return AsyncOpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY",
                "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345",
            ),
            base_url=os.getenv("OPENAI_BASE_URL", "https://sub2api.starysp.top/v1"),
        )

    DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-6.1-sol")


class TicketState(TypedDict):
    """
    【状态契约类】
    该类定义了整个状态图中所有节点共享的状态字段（State Fields），
    以及每个字段的类型约束。
    """

    ticket_id: str
    user_query: str
    category: str
    assigned_team: str
    resolved_message: str


# 【修改 2】修正变量名拼写并替换为“工单分类专用提示词”
# 原本是：system_promt = ("你是一个高智商...请遵循 ReAct 范式...")（会导致模型输出长段废话而不是分类标签）
system_prompt = (
    "你是一个工单意图分类助手。请根据用户输入判断工单类型，并严格只输出以下三个英文单词之一，不要输出任何额外解释或标点：\n"
    "- billing：涉及退款、账单、扣费、发票、续费等财务问题\n"
    "- technical：涉及报错、bug、页面白屏、崩溃、无法登录等技术问题\n"
    "- unknown：无法归入以上两类的其他问题"
)


# 【修改 3】改回 async def + await 异步调用，并真正使用大模型返回的分类结果
# 原本是：
#   def classify_intent_node(...) -> dict:（同步函数里调 AsyncOpenAI 没加 await，response 只是协程对象）
#   return {"category": "technical"}（原本写死了返回值，没用模型结果）
async def classify_intent_node(
    state: TicketState,
) -> Command[Literal["billing", "technical", "fallback"]]:
    """【节点 1：调用大模型进行意图识别与工单分类】"""

    print(f"\n[Node 1: 意图分类] 正在分析工单: {state['ticket_id']}")
    query = state["user_query"].strip()
    client = get_async_openai_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    response = await client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0,
    )
    raw_category = (response.choices[0].message.content or "").strip().lower()
    category = (
        raw_category
        if raw_category in {"billing", "technical", "unknown"}
        else "unknown"
    )
    # 用映射表替代多余的 if/elif，直接决定 Command 的跳转目标
    route_map = {"billing": "billing", "technical": "technical"}
    next_node = route_map.get(category, "fallback")
    return Command(update={"category": category}, goto=next_node)


def billing_handler_node(state: TicketState) -> dict:
    """【节点 2：账单财务专属处理流程】"""
    print("[Node 2: 账单处理] 转发给财务团队接入...")
    return {
        "assigned_team": "财务清算组",
        "resolved_message": "已为您转交财务专员，将在 1 个工作日内核实并原路退回款项。",
    }


def technical_handler_node(state: TicketState) -> dict:
    """【节点 3：研发技术专属处理流程】"""
    print("[Node 3: 技术处理] 转发给研发团队接入...")
    return {
        "assigned_team": "研发技术组",
        "resolved_message": "已为您转交研发专员，将在 2 个工作日内核实并修复问题。",
    }


def manual_fallback_node(state: TicketState) -> dict:
    """【节点 4：兜底人工客服流】"""
    print("[Node 4: 人工客服] 转发给人工客服接入...")
    return {
        "assigned_team": "人工客服组",
        "resolved_message": "已为您转交人工客服专员，将在 1 个工作日内核实并回复您。",
    }


def build_graph():
    from langgraph.graph import END, START, StateGraph

    workflow = StateGraph(TicketState)
    workflow.add_node("classifier", classify_intent_node)
    workflow.add_edge(START, "classifier")

    # 互斥业务分支用字典批量注册并连向 END（classifier 出口由 Command.goto 决定，无需额外连线）
    handlers = {
        "billing": billing_handler_node,
        "technical": technical_handler_node,
        "fallback": manual_fallback_node,
    }
    for name, fn in handlers.items():
        workflow.add_node(name, fn)
        workflow.add_edge(name, END)

    return workflow.compile()


# 【修改 5】改用 async def main() + await app.ainvoke() + asyncio.run(main()) 运行异步图，并打印最终结果
# 原本是：直接在 if __name__ == "__main__": 中调用同步的 res = app.invoke(input_state_1)（无法运行 async 节点，且未打印 res）
async def main():
    try:
        app = build_graph()
        input_state_1 = {
            "ticket_id": "TICK_1001",
            "user_query": "上个月我不小心重复续费了年费会员，可以申请退款吗？",
            "category": "unknown",
            "assigned_team": "none",
            "resolved_message": "",
        }
        res = await app.ainvoke(input_state_1)
        print(
            f"\n[工单处理完毕]:\n"
            f"  -> 识别分类: {res['category']}\n"
            f"  -> 分配团队: {res['assigned_team']}\n"
            f"  -> 答复文案: {res['resolved_message']}"
        )
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
