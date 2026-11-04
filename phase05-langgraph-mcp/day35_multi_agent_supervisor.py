"""
DAY 35 实战源码：多 Agent 协作系统 —— Supervisor 主管派单模式
文件说明：
    单个 Agent 上下文有限，容易在长流程中顾此失彼。
    多 Agent 的经典架构之一是 Supervisor（主考官/架构师）模式：
    - 主管 Agent：分析需求，决定由哪个子 Agent 处理；
    - 子 Agent A（Researcher 研究员）：负责信息收集与知识整合；
    - 子 Agent B（Coder/Writer 交付员）：负责代码实现与文档产出；
    - 最终汇报给 Supervisor 结案。
运行要求：
    pip install langgraph langchain-core
    python day35_multi_agent_supervisor.py
"""

from typing import TypedDict, List, Literal
from langgraph.graph import StateGraph, START, END

# ---------------------------------------------------------------------------
# 1. 多智能体协作状态模型
# ---------------------------------------------------------------------------

class MultiAgentState(TypedDict):
    task_goal: str             # 初始整体任务目标
    research_notes: str        # 研究员产出的背景资料与事实笔记
    code_artifact: str         # 工程师产出的落地代码/方案
    next_actor: str            # 主管决定的下一步执行者
    iterations: int            # 协作轮次计数

# ---------------------------------------------------------------------------
# 2. 模拟各个智能体节点的专业行为
# ---------------------------------------------------------------------------

def supervisor_node(state: MultiAgentState) -> dict:
    """
    主管 Agent (Supervisor)：
    审视当前状态，分配下一步任务给特定专家角色，或宣布完成。
    """
    current_iter = state.get("iterations", 0) + 1
    print(f"\n[👑 Supervisor 主管思考 - 轮次 {current_iter}] 评估目前交付进度...")

    # 如果还没有研究笔记，先派发给研究员
    if not state.get("research_notes"):
        print("主管决策 -> 派发任务给 [Researcher 调研员]")
        return {"next_actor": "researcher", "iterations": current_iter}

    # 如果有研究笔记但还没有落地代码，派发给工程师
    if not state.get("code_artifact"):
        print("主管决策 -> 派发任务给 [Coder 工程师]")
        return {"next_actor": "coder", "iterations": current_iter}

    # 成果全部齐备，结单
    print("主管决策 -> 任务全部高质量完成，宣告结单！")
    return {"next_actor": "finish", "iterations": current_iter}

def researcher_agent_node(state: MultiAgentState) -> dict:
    """子智能体 1：技术调研专家"""
    print(f"[🔍 Researcher] 正在为目标「{state['task_goal']}」检索最新开源方案与最佳实践...")
    notes = (
        "调研报告：\n"
        "1. 业界普遍推荐采用 SSE 进行实时 Token 流式下发；\n"
        "2. 前端可采用 EventSource API 监听自定义事件，实现动态 Generative UI 渲染。"
    )
    return {"research_notes": notes}

def coder_agent_node(state: MultiAgentState) -> dict:
    """子智能体 2：代码工程专家"""
    print(f"[💻 Coder] 正在基于调研专家的笔记落地核心代码架构...")
    code = (
        "// 自动生成的客户端消费组件\n"
        "const sse = new EventSource('/api/agent/stream');\n"
        "sse.onmessage = (e) => renderToken(e.data);"
    )
    return {"code_artifact": code}

# ---------------------------------------------------------------------------
# 3. 路由分支与图编排
# ---------------------------------------------------------------------------

def route_supervisor_decision(state: MultiAgentState) -> Literal["researcher", "coder", "end"]:
    next_step = state["next_actor"]
    if next_step == "researcher":
        return "researcher"
    elif next_step == "coder":
        return "coder"
    return "end"

workflow = StateGraph(MultiAgentState)

# 注册所有智能体角色
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", researcher_agent_node)
workflow.add_node("coder", coder_agent_node)

# 从主管开始
workflow.add_edge(START, "supervisor")

# 主管根据评估结果派发给不同专家
workflow.add_conditional_edges(
    "supervisor",
    route_supervisor_decision,
    {
        "researcher": "researcher",
        "coder": "coder",
        "end": END
    }
)

# 专家完成其专业输出后，统一汇报回主管，由主管重新审视
workflow.add_edge("researcher", "supervisor")
workflow.add_edge("coder", "supervisor")

app = workflow.compile()

# ---------------------------------------------------------------------------
# 测试协作流程
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    task_input = {
        "task_goal": "构建一个支持 Generative UI 的流式全栈 Agent 架构方案",
        "research_notes": "",
        "code_artifact": "",
        "next_actor": "",
        "iterations": 0
    }

    print("🚀 === 启动多 Agent 团队协作工作流 ===")
    final_output = app.invoke(task_input)

    print("\n🎉 === 团队最终交付成果汇总 ===")
    print(f"【调研员成果】：\n{final_output['research_notes']}")
    print(f"\n【工程师产出】：\n{final_output['code_artifact']}")
    print(f"\n【总流转轮次】：{final_output['iterations']} 次")
