"""
DAY 16 实战源码：多 Agent 协作系统 —— Supervisor 主管派单模式
==============================================================================
【文件导读】：
    单一 Agent 在面对复杂大工程时，容易在超长的上下文对话中“顾此失彼”、“注意力稀释”或出现严重的幻觉。
    
    业界解决复杂工程的经典架构之一是【Supervisor 主管调度模式】（又称主考官/架构师模式）：
    - 主管智能体 (Supervisor)：负责全局目标拆解、分配任务给专业专家、验收各专家交付质量并决定何时结单；
    - 专家智能体 A (Researcher 调研员)：专门负责信息检索、知识总结与背景分析；
    - 专家智能体 B (Coder 工程师)：专注依据调研结论落地代码或工程配置文件；
    - 专家完成输出后统一汇报回 Supervisor，由 Supervisor 再次审视，直到满足结单标准。

【核心状态流转拓扑】：
    START -> [Supervisor] --条件分支--> [Researcher] --汇报--> [Supervisor]
                                      --> [Coder]      --汇报--> [Supervisor]
                                      --> [END (宣告完成)]

【运行要求】：
    pip install langgraph langchain-core
    python day16_multi_agent_supervisor.py
==============================================================================
"""

from typing import TypedDict, List, Literal

# ==============================================================================
# 1. 多智能体协作状态契约 (MultiAgentState Schema)
# ==============================================================================

class MultiAgentState(TypedDict):
    """
    【团队共享工作台状态模型】
    整个团队的公共白板，所有角色都可以看到目标和已有的中间产物。
    """
    task_goal: str             # 用户下达的初始总任务目标
    research_notes: str        # 调研专家产出的背景资料与技术调研笔记
    code_artifact: str         # 工程师专家根据调研产出的落地核心代码/配置文件
    next_actor: str            # 主管智能体决策的下一步执行角色名字
    iterations: int            # 团队内部协作流转总轮次（防止死循环）

# ==============================================================================
# 2. 各个智能体节点的专业处理逻辑 (Agent Nodes)
# ==============================================================================

def supervisor_node(state: MultiAgentState) -> dict:
    """
    【主管智能体 (Supervisor)】
    核心职能：相当于团队的技术 Leader 或项目经理。
    审视共享状态中的产出物，决策是由研究员继续补充信息、由工程师编写代码、还是已经完美达标宣告结题。
    """
    current_iter = state.get("iterations", 0) + 1
    print(f"\n[Supervisor 主管思考 - 轮次 {current_iter}] 正在审查目前交付状态...")

    # 决策阶段 1：如果还没有调研笔记，派单给调研员
    if not state.get("research_notes"):
        print("-> 主管决策: 背景资料不足，派发任务给 [Researcher 调研员]")
        return {"next_actor": "researcher", "iterations": current_iter}

    # 决策阶段 2：如果已有调研笔记但还没有工程代码，派单给开发工程师
    if not state.get("code_artifact"):
        print("-> 主管决策: 调研资料已齐备，派发任务给 [Coder 研发工程师]")
        return {"next_actor": "coder", "iterations": current_iter}

    # 决策阶段 3：两项核心产物全部验收合格，结单闭环
    print("-> 主管决策: 需求已高质量闭环，宣告结单！")
    return {"next_actor": "finish", "iterations": current_iter}

def researcher_agent_node(state: MultiAgentState) -> dict:
    """
    【子智能体 1：技术调研专家 (Researcher)】
    专注针对任务目标检索行业最佳实践与开源方案。
    """
    print(f"[Researcher 调研员] 正在针对任务「{state['task_goal']}」检索最新业界方案...")
    notes = (
        "技术方案调研备忘录：\n"
        "1. 数据传输推荐采用 SSE (Server-Sent Events) 协议进行实时轻量级流式推送；\n"
        "2. 前端可采用原生 EventSource 或 fetch-event-source 监听事件，实现动态 Generative UI 渐进渲染。"
    )
    return {"research_notes": notes}

def coder_agent_node(state: MultiAgentState) -> dict:
    """
    【子智能体 2：代码工程专家 (Coder)】
    专注根据调研员整理的要点，编写健壮、可落地的核心代码。
    """
    print(f"[Coder 工程师] 正在基于调研专家的备忘录编写客户端消费逻辑...")
    code = (
        "// 客户端消费 SSE 核心逻辑代码\n"
        "const sse = new EventSource('/api/agent/stream');\n"
        "sse.onmessage = (event) => {\n"
        "    const payload = JSON.parse(event.data);\n"
        "    renderDynamicWidget(payload.ui_type, payload.data);\n"
        "};"
    )
    return {"code_artifact": code}

# ==============================================================================
# 3. 路由分支与状态图编排 (StateGraph Compilation)
# ==============================================================================

def route_supervisor_decision(state: MultiAgentState) -> Literal["researcher", "coder", "end"]:
    """
    【主管决策分流函数】
    读取 supervisor 节点下发的 next_actor 字段，映射到具体的下游节点。
    """
    next_step = state["next_actor"]
    if next_step == "researcher":
        return "researcher"
    elif next_step == "coder":
        return "coder"
    return "end"

def build_supervisor_graph():
    from langgraph.graph import StateGraph, START, END

    workflow = StateGraph(MultiAgentState)

    # 注册团队所有角色节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_agent_node)
    workflow.add_node("coder", coder_agent_node)

    # 流程从主管开始
    workflow.add_edge(START, "supervisor")

    # 主管根据审查结果条件分流
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor_decision,
        {
            "researcher": "researcher",
            "coder": "coder",
            "end": END
        }
    )

    # 【核心流转闭环】：各专家完成工作后，不是直接结束，而是重新流回 supervisor 进行复核验收！
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("coder", "supervisor")

    return workflow.compile()

# ==============================================================================
# 4. 模拟多智能体团队协作运行
# ==============================================================================

if __name__ == "__main__":
    try:
        app = build_supervisor_graph()

        task_input = {
            "task_goal": "构建一个支持 Generative UI 的流式全栈 Agent 架构方案",
            "research_notes": "",
            "code_artifact": "",
            "next_actor": "",
            "iterations": 0
        }

        print("=" * 60)
        print("=== 启动多 Agent 团队协作工作流 ===")
        print("=" * 60)
        final_output = app.invoke(task_input)

        print("\n" + "=" * 60)
        print("=== 团队最终交付成果汇总 ===")
        print("=" * 60)
        print(f"【调研员成果】：\n{final_output['research_notes']}")
        print(f"\n【工程师产出】：\n{final_output['code_artifact']}")
        print(f"\n【协作流转总轮次】：{final_output['iterations']} 轮")

    except ImportError:
        print("[提示] 本地未安装 langgraph 依赖，可执行: pip install langgraph langchain-core 进行安装体验。")
