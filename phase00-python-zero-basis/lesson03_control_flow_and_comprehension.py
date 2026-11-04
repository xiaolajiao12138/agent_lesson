"""
【Python 零基础·课时 03】条件分支、循环与列表推导式（干掉 map 与 filter）
文件说明：
    前端开发者最习惯使用数组的 .map() 和 .filter()。
    在 Python 中，写出地道代码的灵魂是：列表推导式 (List Comprehension)。
    本节彻底攻克缩进规则、循环语法与推导式。
运行方式：
    python lesson03_control_flow_and_comprehension.py
"""

from typing import List, Dict

# ==============================================================================
# 1. 缩进规则与条件判断（对比 JS 的 if...else if...else）
# ==============================================================================
def demo_control_flow():
    print("=== 1. 条件控制流（缩进与 elif） ===")

    # 关键规则：Python 不使用大括号 {} 圈定作用域，严格依靠【4 个空格缩进】！
    # 关键字：if ... elif ... else (注意不是 else if，而是简写的 elif)
    user_role = "admin"
    token_balance = 500

    if user_role == "admin" and token_balance > 100:
        print("-> 权限校验通过：VIP 管理员，拥有无限次智能体调用权。")
    elif user_role == "developer":
        print("-> 权限校验：普通开发者，按 Token 计量扣费。")
    else:
        print("-> 权限不足，请先注册或升级会员。")

    # 三元运算符 (Ternary Operator)
    # JS 写法: const status = isOnline ? "在线" : "离线";
    # Python 写法: 值1 if 条件 else 值2
    is_online = True
    status_text = "智能体在线" if is_online else "智能体已休眠"
    print(f"三元运算符输出状态: {status_text}")


# ==============================================================================
# 2. 循环遍历与实用内置函数（range, enumerate, zip）
# ==============================================================================
def demo_loops():
    print("\n=== 2. 循环与常用迭代工具 ===")

    # 1. 普通 for...in 循环 (类似 JS 的 for (const item of array))
    tasks = ["解析 PDF 文档", "调用向量数据库", "生成结构化报告"]
    print("1. 基础 for...in 遍历:")
    for task in tasks:
        print(f"   执行任务: {task}")

    # 2. 带索引下标的遍历：enumerate() (对标 JS 的 tasks.forEach((item, index) => ...))
    # 在 Python 中千万不要写 for i in range(len(tasks))，标准做法是 enumerate
    print("\n2. 使用 enumerate() 同时获取下标与内容:")
    for index, task in enumerate(tasks, start=0):
        print(f"   步骤 {index}: {task}")

    # 3. 计次循环：range(start, stop, step) (对标 JS 的 for (let i=0; i<5; i++))
    print("\n3. 使用 range(3) 执行固定次数重试循环:")
    for attempt in range(1, 4):
        print(f"   第 {attempt} 次重试连接模型服务器...")

    # 4. 同步联动多个列表：zip() (前端极度眼馋的内置函数！)
    # 将多个等长数组像拉链一样按索引配对成元组
    names = ["GPT-4o", "Claude-3.5-Sonnet", "DeepSeek-V3"]
    latencies = [1.2, 0.9, 0.6]  # 单位：秒
    costs = [0.03, 0.015, 0.002] # 单位：美元/千Token

    print("\n4. 使用 zip() 多数组同步遍历 (类似合并表格行):")
    for name, lat, cost in zip(names, latencies, costs):
        print(f"   模型: {name:<18} | 响应时延: {lat}s | 成本单价: ${cost}")


# ==============================================================================
# 3. 核心大招：列表推导式与字典推导式（对标 JS .map() 与 .filter()）
# ==============================================================================
def demo_comprehensions():
    print("\n=== 3. 列表推导式：像前端写函数式编程一样优雅 ===")

    raw_scores = [65, 88, 45, 92, 59, 78, 100]

    # 需求：筛选出及格（>=60）的分数，并给每人加 5 分奖励分
    # JS 写法：raw_scores.filter(s => s >= 60).map(s => s + 5)
    # Python 列表推导式语法：[ 表达式 for 变量 in 列表 if 过滤条件 ]
    rewarded_scores = [s + 5 for s in raw_scores if s >= 60]
    new_scores = [s+5 for s in raw_scores]
    print (f"每个人加5分 {new_scores}")
    print(f"原始分数: {raw_scores}")
    print(f"及格并加 5 分 (filter+map): {rewarded_scores}")

    # 需求：提取大模型返回的切片文本
    documents = [
        {"id": 1, "title": "React 19 特性", "valid": True},
        {"id": 2, "title": "废弃旧草案", "valid": False},
        {"id": 3, "title": "LangGraph 状态机", "valid": True}
    ]
    # JS: documents.filter(d => d.valid).map(d => d.title)
    valid_titles = [d["title"] for d in documents if d["valid"]]
    print(f"有效文章标题列表: {valid_titles}")

    # 4. 字典推导式 (用于构建映射索引查找表，类似 JS 的 reduce 生成对象)
    # 需求：将标题列表转化为 { "React 19 特性": 长度 } 的查找字典
    title_length_map = {title: len(title) for title in valid_titles}
    print(f"字典推导式结果: {title_length_map}")


if __name__ == "__main__":
    demo_control_flow()
    demo_loops()
    demo_comprehensions()
