"""
DAY 24 实战源码：人机协同与断点恢复（Human-in-the-loop）
文件说明：
    在涉及资金划转、发邮件、删数据库等高危场景中，绝对不能让大模型完全自主行动。
    必须通过“人在回路”在关键节点前中断执行（挂起当前状态），
    等待前端人工确认审批后，再通过会话 ID 恢复流转。
运行要求：
    pip install langgraph langchain-core
    python day24_human_in_the_loop.py
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# ---------------------------------------------------------------------------
# 1. 状态定义
# ---------------------------------------------------------------------------

class DeploymentState(TypedDict):
    project_name: str          # 发布项目名
    env: str                   # 目标环境: 'staging' (测试) | 'prod' (生产)
    deploy_command: str        # 部署指令
    approved_by_admin: bool    # 是否获得管理员审批
    execution_log: str         # 执行结果日志

# ---------------------------------------------------------------------------
# 2. 节点逻辑
# ---------------------------------------------------------------------------

def prepare_node(state: DeploymentState) -> dict:
    """节点 1：生成部署脚本与环境分析"""
    print(f"\n[Node: 准备] 正在打包构建项目: {state['project_name']}，目标环境: {state['env']}")
    cmd = f"deploy-cli --project {state['project_name']} --target {state['env']} --tag v2.0.0"
    return {"deploy_command": cmd}

def admin_approval_node(state: DeploymentState) -> dict:
    """节点 2：人工审查断点节点（图会在此节点前被强制中断挂起）"""
    print(f"[Node: 审批挂起] 🚨 进入生产环境敏感审批流，正在等待外部管理员审核...")
    # 该节点在恢复时，直接接收外部人工修改后的状态
    return {}

def execute_deploy_node(state: DeploymentState) -> dict:
    """节点 3：实际执行发布脚本"""
    if state.get("approved_by_admin", False):
        print(f"[Node: 执行发布] ✅ 审批通过！正在向 {state['env']} 执行指令: {state['deploy_command']}")
        return {"execution_log": f"生产环境发布成功，项目 {state['project_name']} 已上线。"}
    else:
        print(f"[Node: 终止发布] ❌ 审批被驳回！取消发布动作。")
        return {"execution_log": "管理员驳回了生产发布申请，工作流已终止。"}

# ---------------------------------------------------------------------------
# 3. 路由判断与图组装
# ---------------------------------------------------------------------------

def route_by_env(state: DeploymentState) -> Literal["auto_execute", "wait_approval"]:
    """如果发布的不是 prod 生产环境，则不需要人工审批，直接全自动发布"""
    if state["env"] == "prod":
        return "wait_approval"
    return "auto_execute"

workflow = StateGraph(DeploymentState)

workflow.add_node("prepare", prepare_node)
workflow.add_node("approval", admin_approval_node)
workflow.add_node("deploy", execute_deploy_node)

workflow.add_edge(START, "prepare")

# 根据部署目标环境分流
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

# 启用持久化检查点（类似前端的 Redux 状态持久化或浏览器本地快照存储）
checkpointer = MemorySaver()

# 核心：设置 interrupt_before=["approval"]
# 任何到达 approval 节点之前的动作，都会保存快照并暂停，返回控制权给调用者！
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["approval"]
)

# ---------------------------------------------------------------------------
# 4. 模拟前端全生命周期交互
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 会话线程 ID（对应真实业务中的工作流 ID 或 Ticket ID）
    session_config = {"configurable": {"thread_id": "deploy_session_0089"}}

    # 步骤一：前端发起上线生产环境申请
    initial_payload = {
        "project_name": "agent-dashboard-web",
        "env": "prod",
        "deploy_command": "",
        "approved_by_admin": False,
        "execution_log": ""
    }

    print(">>> 【第一阶段】：开发者在前端界面点击提交【生产发布】申请")
    for event in app.stream(initial_payload, config=session_config):
        print(f"流转事件快照: {event}")

    # 检查工作流当前状态
    state_snapshot = app.get_state(session_config)
    print(f"\n[工作流已安全暂停] 当前挂起点: {state_snapshot.next}")
    print(f"生成的待审指令: {state_snapshot.values['deploy_command']}")

    # 步骤二：模拟管理员在后台点击【批准通过】
    print("\n>>> 【第二阶段】：管理员审核无误，在前端界面点击【批准通过】")
    
    # 模拟外部管理员更新图的全局状态
    app.update_state(
        session_config,
        {"approved_by_admin": True},
        as_node="approval"
    )

    # 传入 None 恢复被中断的图继续向下执行
    for event in app.stream(None, config=session_config):
        print(f"恢复后事件快照: {event}")

    # 打印最终落地成果
    final_state = app.get_state(session_config)
    print(f"\n[最终执行说明]: {final_state.values['execution_log']}")
