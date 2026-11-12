"""
DAY 14 实战源码：LangGraph 状态图与工作流编排（前端状态机与 Redux 思想落地）
==============================================================================
【文件导读】：
    当 AI 智能体的业务链路变得复杂（比如包含分支条件、人工审核、多模型轮替、循环重试）时，
    单纯的 if-else 或 while 循环会迅速沦为难以维护的“面条代码”。
    
    LangGraph 是 LangChain 官方推出的现代图编排框架，它将智能体建模为一个“有向状态图”：
    - State (全局状态)：流转在图中的不可变数据模型（直接对标前端 Redux / Pinia Store）
    - Node (节点函数)：纯函数计算单元，接收当前 state，返回局部变更对象（对标 Redux Reducer）
    - Edge (连线与边)：定义执行的流向，分为固定边（Direct Edge）与条件分支边（Conditional Edge）

【前端概念无缝迁移对照】：
    - TypedDict / State <===> TypeScript interface 全局状态接口
    - Node 函数          <===> dispatch 一个 action 触发 reducer 更新 state
    - StateGraph 编译    <===> 创建 Redux Store 并挂载中间件，输出可执行 app 实例

【运行要求】：
    pip install langgraph langchain-core
    python day14_langgraph_basics.py
==============================================================================
"""

from typing import TypedDict, Literal

# ==============================================================================
# 第一步：定义全局状态模型（State Schema）
# ==============================================================================

class TicketState(TypedDict):
    """
    【工单流转全局状态契约】
    对标前端 TypeScript: interface TicketState { ... }
    在整张图从 START 节点流动到 END 节点的整个生命周期中，所有的节点都共享这份状态，
    且只能通过返回增量字典来进行纯函数式的不可变更新。
    """
    ticket_id: str               # 工单唯一标识 ID
    user_query: str              # 用户的初始反馈内容
    category: str                # 工单分类：'billing' (财务账单) | 'technical' (研发技术) | 'unknown' (未知)
    assigned_team: str           # 最终处理与承接该工单的业务团队名称
    resolved_message: str        # 结单说明或返回给用户的答复文案

# ==============================================================================
# 第二步：定义节点处理函数（Nodes）
# ==============================================================================
# 每一个 Node 函数都接收当前最新的 state，并返回一个局部更新的 dict。
# LangGraph 底层会自动执行 { ...state, ...updates } 将新字段浅合并入全局状态。

def classify_intent_node(state: TicketState) -> dict:
    """
    【节点 1：意图识别与自动分类】
    在实际生产中，这里往往是一次对大模型的异步调用，让大模型分析用户语义并分类；
    本示例使用高效关键词做快速归类演示。
    """
    print(f"\n[Node 1: 意图分类] 正在分析工单: {state['ticket_id']}")
    query = state["user_query"].lower()

    if "退款" in query or "钱" in query or "发票" in query or "账单" in query:
        return {"category": "billing"}
    elif "bug" in query or "报错" in query or "无法登录" in query or "崩溃" in query or "typeerror" in query:
        return {"category": "technical"}
    else:
        return {"category": "unknown"}

def billing_handler_node(state: TicketState) -> dict:
    """【节点 2：账单财务专属处理流程】"""
    print(f"[Node 2: 账单处理] 转发给财务团队接入...")
    return {
        "assigned_team": "财务清算组",
        "resolved_message": "已为您转交财务专员，将在 1 个工作日内核实并原路退回款项。"
    }

def technical_handler_node(state: TicketState) -> dict:
    """【节点 3：研发技术支持专属处理流程】"""
    print(f"[Node 3: 技术处理] 转发给 DevOps 与研发团队接入...")
    return {
        "assigned_team": "前端/平台技术支持组",
        "resolved_message": "技术专家已捕获此错误日志，正排查灰度版本服务。"
    }

def manual_fallback_node(state: TicketState) -> dict:
    """【节点 4：兜底人工客服流】"""
    print(f"[Node 4: 兜底流转] 无法自动归类，转人工坐席...")
    return {
        "assigned_team": "人工 VIP 客服组",
        "resolved_message": "您的问题较为复杂，已为您接通人工 VIP 专席。"
    }

# ==============================================================================
# 第三步：条件分支路由函数（Conditional Routing）
# ==============================================================================

def route_ticket(state: TicketState) -> Literal["billing", "technical", "fallback"]:
    """
    【条件边分支路由】
    纯逻辑判断函数：不修改任何状态，仅根据 state 中的 category 字段返回一个字符串标签，
    LangGraph 根据此标签决定下一个要唤醒并执行的下游节点。
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

def build_workflow_app():
    from langgraph.graph import StateGraph, START, END

    # 1. 初始化图对象，传入 State 契约类型
    workflow = StateGraph(TicketState)

    # 2. 注册所有可执行的节点（名字 -> 对应函数）
    workflow.add_node("classifier", classify_intent_node)
    workflow.add_node("billing_service", billing_handler_node)
    workflow.add_node("technical_service", technical_handler_node)
    workflow.add_node("fallback_service", manual_fallback_node)

    # 3. 编排连线（Edges）：
    # 从图的起点 START，无条件流向分类节点 classifier
    workflow.add_edge(START, "classifier")

    # 条件路由：从 classifier 节点出发，经过 route_ticket 判断，映射分流到 3 个下游服务
    workflow.add_conditional_edges(
        "classifier",
        route_ticket,
        {
            "billing": "billing_service",
            "technical": "technical_service",
            "fallback": "fallback_service"
        }
    )

    # 汇流：无论进入哪个业务服务节点，处理完成后都统一连向 END 节点结束流程
    workflow.add_edge("billing_service", END)
    workflow.add_edge("technical_service", END)
    workflow.add_edge("fallback_service", END)

    # 4. 编译图，生成可被调用的 app 实例
    return workflow.compile()

# ==============================================================================
# 第五步：本地测试运行
# ==============================================================================

if __name__ == "__main__":
    try:
        app = build_workflow_app()

        # ----------------------------------------------------------------------
        # 测试案例 1：技术报错工单
        # ----------------------------------------------------------------------
        input_state_1 = {
            "ticket_id": "TICK_1001",
            "user_query": "点击登录按钮后页面白屏，Console 报 Uncaught TypeError 错误！",
            "category": "unknown",
            "assigned_team": "none",
            "resolved_message": ""
        }
        
        print("=" * 60)
        print("=== 测试案例 1：技术工单流转测试 ===")
        print("=" * 60)
        result_1 = app.invoke(input_state_1)
        print(f"\n[工单处理完毕]:\n  -> 分配团队: {result_1['assigned_team']}\n  -> 答复文案: {result_1['resolved_message']}")

        # ----------------------------------------------------------------------
        # 测试案例 2：财务退费工单
        # ----------------------------------------------------------------------
        input_state_2 = {
            "ticket_id": "TICK_1002",
            "user_query": "上个月我不小心重复续费了年费会员，可以申请退款吗？",
            "category": "unknown",
            "assigned_team": "none",
            "resolved_message": ""
        }
        
        print("\n" + "=" * 60)
        print("=== 测试案例 2：财务工单流转测试 ===")
        print("=" * 60)
        result_2 = app.invoke(input_state_2)
        print(f"\n[工单处理完毕]:\n  -> 分配团队: {result_2['assigned_team']}\n  -> 答复文案: {result_2['resolved_message']}")

    except ImportError:
        print("[提示] 本地未安装 langgraph 依赖，可执行: pip install langgraph langchain-core 进行安装体验。")
