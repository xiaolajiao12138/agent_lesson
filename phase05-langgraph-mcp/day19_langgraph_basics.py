"""
DAY 19 实战源码：LangGraph 状态图与工作流编排（前端状态机思想落地）
文件说明：
    当 Agent 逻辑复杂后，单纯的 while 循环会变成难以维护的面条代码。
    LangGraph 将业务建模为一个有向图：
    - State: 全局只读不可变状态对象（类似 Redux Store）
    - Node: 处理函数，接收 state，计算后返回增量字段（类似 Redux Reducer）
    - Edge: 跳转流转关系（普通边 + 条件分支边）
运行要求：
    pip install langgraph langchain-core
    python day19_langgraph_basics.py
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

# ==============================================================================
# 第一步：定义全局状态模型（State Schema）
# ==============================================================================

class TicketState(TypedDict):
    """
    工单流转全局状态接口（类似 TypeScript interface TicketState）
    在整个图的流转过程中，每个 Node 都可以读取并向其合并数据。
    """
    ticket_id: str               # 工单 ID
    user_query: str              # 用户反馈的问题描述
    category: str                # 工单分类：'billing' (账单) | 'technical' (技术) | 'unknown'
    assigned_team: str           # 最终指派处理的组别
    resolved_message: str        # 结单说明

# ==============================================================================
# 第二步：定义节点处理函数（Nodes）
# ==============================================================================

def classify_intent_node(state: TicketState) -> dict:
    """
    节点 1：工单意图识别与自动分类
    模拟大模型根据用户输入，分类为账单或技术问题
    """
    print(f"\n[Node: 意图分类] 正在分析工单: {state['ticket_id']}")
    query = state["user_query"].lower()

    if "退款" in query or "钱" in query or "发票" in query or "账单" in query:
        return {"category": "billing"}
    elif "bug" in query or "报错" in query or "无法登录" in query or "崩溃" in query:
        return {"category": "technical"}
    else:
        return {"category": "unknown"}

def billing_handler_node(state: TicketState) -> dict:
    """节点 2：账单财务专属处理流程"""
    print(f"[Node: 账单处理] 转发给财务团队接入...")
    return {
        "assigned_team": "财务清算组",
        "resolved_message": "已为您转交财务专员，将在 1 个工作日内核实并原路退回款项。"
    }

def technical_handler_node(state: TicketState) -> dict:
    """节点 3：研发技术支持专属处理流程"""
    print(f"[Node: 技术处理] 转发给 DevOps 与研发团队接入...")
    return {
        "assigned_team": "前端/平台技术支持组",
        "resolved_message": "技术专家已捕获此错误日志，正排查灰度版本服务。"
    }

def manual_fallback_node(state: TicketState) -> dict:
    """节点 4：兜底人工客服流"""
    print(f"[Node: 兜底] 无法自动归类，转人工坐席...")
    return {
        "assigned_team": "人工 VIP 客服组",
        "resolved_message": "您的问题较为复杂，已为您接通人工 VIP 专席。"
    }

# ==============================================================================
# 第三步：条件分支路由函数（Conditional Routing）
# ==============================================================================

def route_ticket(state: TicketState) -> Literal["billing", "technical", "fallback"]:
    """
    条件边路由判断：
    根据 state 中的 category 字段，决定走向哪一个下游节点
    """
    cat = state["category"]
    if cat == "billing":
        return "billing"
    elif cat == "technical":
        return "technical"
    return "fallback"

# ==============================================================================
# 第四步：构建并编译状态图（StateGraph）
# ==============================================================================

# 1. 初始化图，指定状态类型
workflow = StateGraph(TicketState)

# 2. 向图中添加节点
workflow.add_node("classifier", classify_intent_node)
workflow.add_node("billing_service", billing_handler_node)
workflow.add_node("technical_service", technical_handler_node)
workflow.add_node("fallback_service", manual_fallback_node)

# 3. 编排边连接
# 从 START 节点直接进入分类器
workflow.add_edge(START, "classifier")

# 从分类器出发，根据路由函数结果，分流到不同业务服务节点
workflow.add_conditional_edges(
    "classifier",
    route_ticket,
    {
        "billing": "billing_service",
        "technical": "technical_service",
        "fallback": "fallback_service"
    }
)

# 业务处理完毕后，全部汇流到 END 结束
workflow.add_edge("billing_service", END)
workflow.add_edge("technical_service", END)
workflow.add_edge("fallback_service", END)

# 编译图为可执行应用
app = workflow.compile()

# ==============================================================================
# 测试运行
# ==============================================================================

if __name__ == "__main__":
    # 测试案例 1：技术报错工单
    input_state_1 = {
        "ticket_id": "TICK_1001",
        "user_query": "点击登录按钮后页面白屏，Console 报 Uncaught TypeError 错误！",
        "category": "unknown",
        "assigned_team": "none",
        "resolved_message": ""
    }
    
    print("=== 测试案例 1：技术工单流转 ===")
    result_1 = app.invoke(input_state_1)
    print(f"最终结果: 分配给 -> {result_1['assigned_team']} | 答复 -> {result_1['resolved_message']}")

    # 测试案例 2：账单退费工单
    input_state_2 = {
        "ticket_id": "TICK_1002",
        "user_query": "上个月我不小心重复续费了年费会员，可以申请退款吗？",
        "category": "unknown",
        "assigned_team": "none",
        "resolved_message": ""
    }
    
    print("\n=== 测试案例 2：财务工单流转 ===")
    result_2 = app.invoke(input_state_2)
    print(f"最终结果: 分配给 -> {result_2['assigned_team']} | 答复 -> {result_2['resolved_message']}")
