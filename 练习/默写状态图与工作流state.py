# 1,初始化app，然后调用 app.ainvoke() 传入问题
# 2，初始化state，将定义的 TicketState 传入 workflow.compile()
# workflow.add_node("classifier", classify_intent_node)workflow添加所有的节点和方法
# workflow.add_edge(START, "classifier") 从classidier开始执行代码
# workflow.add_conditional_edges(
#     "classifier",
#     route_ticket, 根据classifier节点返回值，根据返回值去匹配字典里面的key然后去执行对应的节点
#     {
#         "billing": "billing_service",
#         "technical": "technical_service",
#         "fallback": "fallback_service",
#     },
# )从classifier节点出来后立马进入route_ticket方法，返回值是billing/technical/fallback，去匹配字典里的key，找到对应的节点
# workflow.add_edge("billing_service", END)  # billing_service节点执行完后，进入END节点
# workflow.add_edge("technical_service", END)  # technical_service节点执行完后，进入END节点
# workflow.add_edge("fallback_service", END)  # fallback_service节点执行完后，进入END节点
# 所有的节点结束后都统一进入END节点，结束整个流程
# workflow.compile() 生成可被调用的 app 实例
