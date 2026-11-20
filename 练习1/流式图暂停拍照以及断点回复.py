from typing import TypedDict


class DeploymentState(TypedDict):
    project_name: str
    env: str
    deploy_command: str
    approved_by_admin: bool
    execution_log: str


def prepase_node(state: DeploymentState):
    print(
        f"\n[Node: 准备节点] 正在打包构建项目: {state['project_name']}，目标环境: {state['env']}"
    )
    cmd = f"deploy-cli --project {state['project_name']} --target {state['env']} --tag v2.0.0"
    return {"deploy_command": cmd}


def execute_deploy_node(state: DeploymentState):
    from langgraph.types import interrupt

    if state["env"] == "prd":
        approved = interrupt(f"高危操作，即将执行{state['deploy_command']}，是否批准？")
        if not approved:
            return {"execution_log": "管理员驳回了申请"}
        return {"execution_log": "f发布成功：{state['deploy_command']}"}


def build_workflow():
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import START, StateGraph

    workflow = StateGraph(DeploymentState)
    workflow.add_sequence([("prepase", prepase_node), ("execute", execute_deploy_node)])
    workflow.add_edge(START, "prepase")
    return workflow.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    try:
        seeion_config = {"configurable": {"thread_id": "123456"}}
        initdata = {
            "project_name": "web",
            "env": "prd",
            "deploy_command": "",
            "approved_by_admin": False,
            "execution_log": "",
        }

        app = build_workflow()
        for event in app.stream(initdata, config=seeion_config):
            print(f"{event}")
        snapshot = app.get_state(seeion_config)
        print("当前卡在:", snapshot.next)
        # print(json.dumps(snapshot))
        print(f"生成的待审指令：{snapshot.values['deploy_command']}")
    except Exception as e:
        print(e)
