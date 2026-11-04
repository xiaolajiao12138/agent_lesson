"""
【Python 零基础·课时 02】列表 (List) 与字典 (Dict) 常用方法深度实战
文件说明：
    在 Agent 开发中，90% 的数据操作都是在处理列表（历史消息 messages: list）
    和字典（工具入参、JSON 结构体 dict）。
    本文件对比 JS 的 Array 和 Object，全面实战最核心的内置方法。
运行方式：
    python lesson02_list_dict_methods.py
"""

from typing import List, Dict, Any

# ==============================================================================
# 1. 列表 (List) 核心方法 —— 对标 JS 中的 Array
# ==============================================================================
def demo_list_methods():
    print("=== 1. 列表 (List) 常用方法深度实操（对标 JS Array） ===")

    # 声明一个列表，类似 JS: let tools = ["web_search", "calculator"];
    tools: List[str] = ["web_search", "calculator"]
    print(f"初始工具列表: {tools}")

    # 1. 添加元素到末尾 (类似 JS 的 .push())
    tools.append("python_interpreter")
    print(f"1. .append('python_interpreter') 后: {tools}")

    # 2. 插入元素到指定索引位置 (类似 JS 的 .splice(index, 0, item))
    # 将 'rag_retriever' 插入到第 0 位（最前面）
    tools.insert(0, "rag_retriever")
    print(f"2. .insert(0, 'rag_retriever') 后: {tools}")

    # 3. 弹出/删除元素 (类似 JS 的 .pop())
    # 默认弹出最后一个，也可以传入索引弹出指定位置，如 tools.pop(0) 类似 JS 的 .shift()
    last_tool = tools.pop()
    print(f"3. .pop() 弹出最后一个工具: {last_tool}，当前剩余: {tools}")

    # 4. 根据值直接删除元素 (JS 没有内置按值删除方法，通常需要 indexOf + splice)
    tools.remove("calculator")
    print(f"4. .remove('calculator') 按名称移除后: {tools}")

    # 5. 合并列表 (类似 JS 的 .concat() 或 [...arr1, ...arr2])
    extra_tools = ["email_sender", "database_query"]
    # 方式 A：使用 .extend() 方法原地追加
    tools.extend(extra_tools)
    print(f"5. .extend() 合并多个列表: {tools}")

    # 6. 判断元素是否存在 (类似 JS 的 .includes() 或 indexOf !== -1)
    # Python 语法极其自然：'item' in 列表
    has_search = "web_search" in tools
    print(f"6. 'web_search' in tools (是否存在): {has_search}")

    # 7. 获取元素下标 (类似 JS 的 .indexOf())
    search_idx = tools.index("web_search")
    print(f"7. .index('web_search') 获取下标: {search_idx}")

    # 8. 列表切片 (极度强大！对标 JS 的 .slice())
    # 语法：list[起始索引:结束索引(不含):步长]
    numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print(f"8. 切片 numbers[0:3] (前3项): {numbers[0:3]}")       # [0, 1, 2]
    print(f"   切片 numbers[-2:] (倒数前两项): {numbers[-2:]}")    # [8, 9]
    print(f"   切片 numbers[::2] (隔一个取一个/步长为2): {numbers[::2]}") # [0, 2, 4, 6, 8]
    print(f"   切片 numbers[::-1] (反转列表，类似 .reverse()): {numbers[::-1]}")
    print(f" 切片倒数 每隔三个取一个 {numbers[::-3]}") 

# ==============================================================================
# 2. 字典 (Dict) 核心方法 —— 对标 JS 中的 Object / Map
# ==============================================================================
def demo_dict_methods():
    print("\n=== 2. 字典 (Dict) 常用方法深度实操（对标 JS Object） ===")

    # 声明一个字典，键必须是字符串或不可变类型
    # 类似 JS: const agentState = { current_node: "classifier", retry_count: 0 };
    agent_state: Dict[str, Any] = {
        "current_node": "classifier",
        "retry_count": 0,
        "is_completed": False
    }
    print(f"初始 Agent 状态: {agent_state}")

    # 1. 安全读取属性：.get() 方法（防止 KeyError 崩溃）
    # JS 中: agentState.model_name 如果不存在会返回 undefined，不会报错
    # 但 Python 中如果直接 agent_state["model_name"] 会直接抛出 KeyError 异常崩溃！
    # 必须使用 .get(key, 默认值)
    model = agent_state.get("model_name", "默认模型: gpt-4o")
    print(f"1. .get('model_name', 默认值): {model}")

    # 2. 添加或修改键值对 (类似 JS: agentState.model_name = 'deepseek-v3')
    agent_state["model_name"] = "deepseek-v3"
    print(f"2. 直接赋值添加字段后: {agent_state}")

    # 3. 合并字典 (类似 JS 的 Object.assign(target, source) 或 { ...obj1, ...obj2 })
    patch_data = {"retry_count": 1, "next_node": "tool_executor"}
    # 方式 A：.update()
    agent_state.update(patch_data)
    print(f"3. .update() 合并字典后: {agent_state}")

    # 4. 获取所有的 Keys、Values、Items
    # 类似 JS: Object.keys(obj)、Object.values(obj)、Object.entries(obj)
    keys_list = list(agent_state.keys())
    values_list = list(agent_state.values())
    print(f"4. 所有键 keys(): {keys_list}")
    print(f"   所有值 values(): {values_list}")

    # 遍历字典的标配方式：.items() 返回 (key, value) 元组对
    print("   遍历键值对 (类似 for of Object.entries):")
    for k, v in agent_state.items():
        print(f"   -> 属性 [{k}] = {v}")

    # 5. 删除字段 (类似 JS 的 delete agentState.retry_count)
    # 使用 del 关键字或 .pop()
    deleted_val = agent_state.pop("retry_count", None)
    print(f"5. .pop('retry_count') 删除并返回值: {deleted_val}")

    # 6. 检查 Key 是否存在于字典中 (类似 JS 的 'key' in obj 或 obj.hasOwnProperty('key'))
    has_node = "current_node" in agent_state
    print(f"6. 'current_node' in agent_state (检查键是否存在): {has_node}")


if __name__ == "__main__":
    demo_list_methods()
    demo_dict_methods()
