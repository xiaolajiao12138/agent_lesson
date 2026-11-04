# 阶段三：Tool Calling 与手写 ReAct 智能体（第 4 ~ 5 周）

## 🎯 阶段学习目标
1. 彻底弄懂：从普通“聊天机器人（Chatbot）”进化为“智能体（Agent）”的质变点是什么。
2. 掌握 **Function Calling / Tool Use** 的完整底层通信协议与闭环流程。
3. 掌握经典 **ReAct（Reasoning + Acting）范式**：思考 -> 行动 -> 观察 -> 再思考。
4. **不依赖任何黑盒框架（不用 LangChain）**，纯手写实现一个具备多工具调用能力的自主 Agent 循环。

---

## 🧠 1. Agent 与普通 Chatbot 的本质区别

* **普通 Chatbot**：只能“动嘴”。知识被固化在模型训练的权重里，不会查数据库，无法执行外部命令，遇到不知道的问题容易产生幻觉。
* **智能体（Agent）**：具备“手脚”。遇到问题会自主规划，调用真实世界的计算器、搜索外部网页、查询企业内部 MySQL 数据库，再根据执行结果总结输出。

```
              ┌──────────────────────────────────────────────┐
              │ 用户提问: "帮我查询用户101的余额，并折算成美元"   │
              └──────────────────────┬───────────────────────┘
                                     │
                                     ▼
           ┌──────────────────────────────────────────────────┐
           │ LLM 思考 (Reasoning): 我需要先查余额，再查实时汇率   │
           │ LLM 决策 (Action): 调用 `query_user_balance(101)` │
           └─────────────────────────┬────────────────────────┘
                                     │ (返回 tool_calls)
                                     ▼
             本地执行代码: 查询数据库，得到结果 7200 元人民币 (Observation)
                                     │
                                     ▼
           ┌──────────────────────────────────────────────────┐
           │ LLM 再次思考: 拿到余额了，现在需要查汇率            │
           │ LLM 决策: 调用 `get_exchange_rate("USD", "CNY")`  │
           └─────────────────────────┬────────────────────────┘
                                     │ (返回 tool_calls)
                                     ▼
             本地执行代码: 调汇率 API，得到 7.2 (Observation)
                                     │
                                     ▼
           ┌──────────────────────────────────────────────────┐
           │ LLM 最终回答: "用户101当前余额为 7200 元，折合约 1000 美元。" │
           └──────────────────────────────────────────────────┘
```

---

## 🛠️ 2. Function Calling 的四步闭环协议

这是所有商业级 Agent 底层最重要的通信协议：

1. **定义工具清单**：以 JSON Schema（或 Pydantic/Zod）描述工具名、描述和入参格式，连同用户问题传给模型。
2. **模型自主判定**：模型发现现有知识无法回答，返回特殊的 `finish_reason: "tool_calls"`，并包含要调用的工具名称与 JSON 格式入参。
3. **本地代码执行**：你的服务端拦截到这个请求，在本地运行真实代码（如查库或调第三方接口），拿到结果。
4. **回传观察结果**：把执行结果以 `role: "tool"` 再次发给模型，模型将根据结果生成最终的人类可读答案。

---

## 💻 3. 纯手写原生 ReAct Agent 循环实战（Python）

不要一上来就被 LangChain 的封装搞晕，先手写一次原生循环，终身受用：

```python
import json
from openai import OpenAI

client = OpenAI()

# 1. 真实业务工具定义
def query_order_status(order_id: str) -> str:
    """查询订单的发货状态与物流单号"""
    database = {
        "ORD1001": {"status": "已发货", "tracking_no": "SF12345678"},
        "ORD1002": {"status": "待付款", "tracking_no": None},
    }
    order = database.get(order_id)
    return json.dumps(order if order else {"error": "未查到该订单"})

def cancel_order(order_id: str) -> str:
    """取消订单"""
    return json.dumps({"status": "success", "msg": f"订单 {order_id} 已成功取消"})

# 2. 映射工具函数表
available_tools = {
    "query_order_status": query_order_status,
    "cancel_order": cancel_order,
}

# 3. 声明给模型的工具 Schema
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "query_order_status",
            "description": "查询指定订单编号的当前状态及物流信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单编号，如 ORD1001"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "取消指定的待付款订单",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单编号"}
                },
                "required": ["order_id"],
            },
        },
    },
]

# 4. Agent 核心执行循环（Agent Loop）
def run_agent_loop(user_query: str, max_turns: int = 5):
    messages = [
        {"role": "system", "content": "你是一个电商售后智能助手，必须借助工具解决用户问题。"},
        {"role": "user", "content": user_query},
    ]

    for turn in range(max_turns):
        print(f"\n--- [第 {turn + 1} 轮推理] ---")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        messages.append(msg)

        # 检查是否需要调用工具
        if not msg.tool_calls:
            print("\n[任务完成，最终回复]:\n", msg.content)
            return msg.content

        # 遍历执行所有模型申请调用的工具
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"[Agent 决策调用工具]: {func_name}, 参数: {func_args}")

            # 本地真实执行
            func = available_tools.get(func_name)
            tool_result = func(**func_args) if func else json.dumps({"error": "未知工具"})
            print(f"[工具执行结果]: {tool_result}")

            # 将观察结果传回上下文
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    print("已达到最大循环次数，防止死循环。")

# 测试运行
run_agent_loop("你好，请帮我查一下我的订单 ORD1001 目前状态怎么样了？")
```

---

## 📋 阶段三实战作业

1. 运行并调试上述代码，观察控制台里的每一个轮次变化。
2. **扩展工具**：给 Agent 新增一个“计算两个数字乘积”的本地工具和“查询实时天气”的 Mock 工具。
3. **复合提问测试**：输入：“帮我查下 ORD1001 的状态，另外如果我买两件 99 元的东西一共是多少钱？”，观察 Agent 是否能连续调用多个工具完成复合任务。
4. **思考题**：如果工具调用失败或入参格式不合法，Agent 应该如何自我纠错（Self-Correction）？
