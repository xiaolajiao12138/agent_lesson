"""
DAY 24 实战源码：人机协同与断点恢复（Human-in-the-loop 人在回路机制）
==============================================================================
【文件导读】：
    在涉及资金划转、合同签署、发送全员邮件、执行生产发布或删库等高危操作中，
    绝对不能把控制权 100% 毫无保留地交给大模型。
    
    “人在回路 (Human-in-the-loop)”是高可靠企业级 Agent 架构的生命线：
    在危险动作触发前，状态机自动将执行挂起并生成快照，将控制权交还前端界面；
    等待管理员在审批后台查看、核对甚至修改参数后点击“批准”，
    系统通过唯一的会话 thread_id 重新唤醒并恢复流转。

【核心技术关键点】：
    1. Checkpointer (检查点持久化存储)：
       使用 MemorySaver（或生产环境 PostgresSaver），在每个节点执行前后记录 State 快照。
    2. interrupt_before (前置中断断点)：
       配置 interrupt_before=["approval"]，告知引擎只要下一个准备执行的节点是 approval，就强制挂起。
    3. app.update_state() 与恢复：
       外部通过 update_state 模拟前端人工提交审批数据，然后调用 app.stream(None) 恢复执行。

【运行要求】：
    pip install langgraph langchain-core
    python day24_human_in_the_loop.py
==============================================================================
"""

from typing import TypedDict, Literal

# ==============================================================================
# 1. 状态定义 (State Schema)
# ==============================================================================

class DeploymentState(TypedDict):
    """
    【部署流水线全局状态模型】
    存储整个发布流程中的工程参数、环境标识、审批状态及最终执行日志。
    """
    project_name: str          # 待发布的项目工程名
    env: str                   # 目标部署环境: 'staging' (测试环境) | 'prod' (生产环境)
    deploy_command: str        # 自动拼装生成的真实部署 CLI 命令
    approved_by_admin: bool    # 是否获得管理员的人工授权确认
    execution_log: str         # 最终部署日志记录

# ==============================================================================
# 2. 节点逻辑 (Nodes)
# ==============================================================================

def prepare_node(state: DeploymentState) -> dict:
    """
    【节点 1：生成部署命令与预检】
    Agent 自动分析当前项目配置，组装生产或测试部署指令
    """
    print(f"\n[Node: 准备节点] 正在打包构建项目: {state['project_name']}，目标环境: {state['env']}")
    cmd = f"deploy-cli --project {state['project_name']} --target {state['env']} --tag v2.0.0"
    return {"deploy_command": cmd}

def admin_approval_node(state: DeploymentState) -> dict:
    """
    【节点 2：人工审查断点节点】
    注意：在编译图时我们配置了 interrupt_before=["approval"]，
    因此状态流转到这里时会被强行打断挂起，不会立刻执行内部逻辑。
    当外部管理员在前端点击审批通过并唤醒恢复后，该节点才会接收外部注入的状态继续流转。
    """
    print(f"[Node: 审批节点] [警告] 进入生产环境敏感审批流，正在等待外部管理员审核...")
    return {}

def execute_deploy_node(state: DeploymentState) -> dict:
    """
    【节点 3：实际执行发布脚本】
    根据 state 中的 approved_by_admin 标记，决定执行真实发布或终止撤销。
    """
    if state.get("approved_by_admin", False):
        print(f"[Node: 执行发布] [审核通过] 正在向 {state['env']} 执行指令: {state['deploy_command']}")
        return {"execution_log": f"生产环境发布成功，项目 {state['project_name']} 已平滑上线。"}
    else:
        print(f"[Node: 终止发布] [审核驳回] 管理员未批准，取消发布动作。")
        return {"execution_log": "管理员驳回了生产发布申请，工作流已安全终止。"}

# ==============================================================================
# 3. 路由判断与图组装 (StateGraph Compilation)
# ==============================================================================

def route_by_env(state: DeploymentState) -> Literal["auto_execute", "wait_approval"]:
    """
    【分流条件函数】：
    如果发布的只是测试环境 (staging)，风险较低，直接全自动跳过审批执行发布；
    如果目标环境是生产环境 (prod)，强制重定向到审批流。
    """
    if state["env"] == "prod":
        return "wait_approval"
    return "auto_execute"

def build_workflow():
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver

    workflow = StateGraph(DeploymentState)

    # 注册节点
    workflow.add_node("prepare", prepare_node)
    workflow.add_node("approval", admin_approval_node)
    workflow.add_node("deploy", execute_deploy_node)

    # 编排图连接流向
    workflow.add_edge(START, "prepare")

    # 环境条件分支分流
    workflow.add_conditional_edges(
        "prepare",
        route_by_env,
        {
            "wait_approval": "approval",
            "auto_execute": "deploy"
        }
    )

    workflow.add_edge("approval", "deploy")
    workflow.add_edge("deploy", END)

    # 启用快照检查点（在内存中持久化存储每个步骤的历史状态）
    checkpointer = MemorySaver()

    # 【核心配置】：interrupt_before=["approval"]
    # 任何流向 approval 节点的操作都会在执行前自动保存快照并暂停，等待外部人工介入！
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval"]
    )
    return app

# ==============================================================================
# 4. 模拟前端全生命周期交互
# ==============================================================================

if __name__ == "__main__":
    try:
        app = build_workflow()

        # 会话线程 ID（对应真实业务场景中的发布工单 ID 或 WebSocket 客户端会话）
        session_config = {"configurable": {"thread_id": "deploy_session_0089"}}

        # ----------------------------------------------------------------------
        # 阶段一：前端发起上线生产环境申请
        # ----------------------------------------------------------------------
        initial_payload = {
            "project_name": "agent-dashboard-web",
            "env": "prod",
            "deploy_command": "",
            "approved_by_admin": False,
            "execution_log": ""
        }

        print("=" * 60)
        print(">>> 【第一阶段】：开发者在前端界面点击提交【生产发布】申请")
        print("=" * 60)
        
        # 触发流式执行，图会自动在进入 approval 之前挂起
        for event in app.stream(initial_payload, config=session_config):
            print(f"流转事件快照: {event}")

        # 检查当前快照状态
        state_snapshot = app.get_state(session_config)
        print(f"\n[工作流已被引擎安全拦截挂起！]")
        print(f"  -> 当前待决节点: {state_snapshot.next}")
        print(f"  -> 生成的待审指令: {state_snapshot.values['deploy_command']}")
        print(f"  -> 等待人工管理员介入审批...")

        # ----------------------------------------------------------------------
        # 阶段二：模拟管理员在前端管理后台点击【批准通过】
        # ----------------------------------------------------------------------
        print("\n" + "=" * 60)
        print(">>> 【第二阶段】：管理员审核待执行指令无误，在管理后台点击【批准通过】")
        print("=" * 60)
        
        # 模拟前端接口调用后端：更新该 thread_id 的状态字段
        app.update_state(
            session_config,
            {"approved_by_admin": True},
            as_node="approval"  # 指定是以 approval 节点的身份提交更新
        )

        # 传入 None 恢复被中断挂起的工作流，使其继续向下流转
        for event in app.stream(None, config=session_config):
            print(f"恢复流转事件快照: {event}")

        # 获取最终执行完毕后的完整状态
        final_state = app.get_state(session_config)
        print(f"\n[最终执行说明]: {final_state.values['execution_log']}")

    except ImportError:
        print("[提示] 本地未安装 langgraph 依赖，可执行: pip install langgraph langchain-core 进行安装体验。")
