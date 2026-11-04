"""
================================================================================
【自我测验】Lesson 01 ~ 03 核心知识点实战巩固
================================================================================
使用说明：
    1. 请在每个题目下方的 【TODO】 区域写出你的代码。
    2. 打开终端运行：
       python quiz_lesson01_to_03.py
    3. 查看运行结果是否符合预期！
"""

# ==============================================================================
# 📝 第一题：字符串方法与 f-string（考查 Lesson 01）
# ==============================================================================
def question_one():
    print("\n--- 第一题：字符串清洗与拼接 ---")
    raw_reply = "   welcome to agent world   "

    # 【TODO 1-1】: 去掉 raw_reply 首尾的空白字符，并将其全部转为大写
    # 提示：可以连续链式调用两个方法
    clean_reply = raw_reply.strip().upper()  # 请将 None 替换为你的代码
    # 【TODO 1-2】: 使用 f-string 拼装成："【AI响应】: WELCOME TO AGENT WORLD"
    final_message = f"【AI响应】:{clean_reply}"  # 请将 None 替换为你的代码

    print(f"你的处理结果: {clean_reply}")
    print(f"你的拼接结果: {final_message}")


# ==============================================================================
# 📝 第二题：列表切片与字典安全取值（考查 Lesson 02）
# ==============================================================================
def question_two():
    print("\n--- 第二题：切片技巧与字典防崩溃 ---")
    
    # 场景 A：切片取尾部
    messages = [
        "User: 你好",
        "AI: 在的，请问有什么可以帮你？",
        "User: 帮我查一下北京天气",
        "AI: 今天北京晴天，25度"
    ]
    # 【TODO 2-1】: 使用【切片】语法，取出最后 2 条消息
    latest_two = messages[-2:]  # 请将 None 替换为你的代码，如 messages[???]
    print(f"截取到的最后两条消息: {latest_two}")

    # 场景 B：字典安全取值
    model_config = {
        "model": "gpt-4o",
        "temperature": 0.7
    }
    # 【TODO 2-2】: 
    # 从 model_config 中读取 "max_tokens" 字段。
    # 注意：字典里没有这个 key！不能写 model_config["max_tokens"]（会报错崩溃）。
    # 请使用安全读取方法，如果不存在则返回默认值 2048。
    max_tokens = model_config.get('max_tokens',2048)  # 请将 None 替换为你的代码
    print(f"读取到的 max_tokens: {max_tokens}")


# ==============================================================================
# 📝 第三题：循环迭代与推导式清洗（考查 Lesson 03）
# ==============================================================================
def question_three():
    print("\n--- 第三题：循环工具与列表推导式 ---")

    # 场景 A：带序号的遍历
    tools = ["web_search", "calculator", "database_query"]
    print("工具列表打印展示：")
    # 【TODO 3-1】: 
    # 请使用 Python 最推荐的内置函数（不要用 range(len(tools))），
    # 在 for 循环中同时拿到 index (下标 0, 1, 2) 和 tool (工具名) 并打印
    # 示例打印格式：
    # 下标 0 -> web_search
    # 下标 1 -> calculator
    # 下标 2 -> database_query
    pass  # 请在此处写你的 for 循环代码
    for index,val in enumerate(tools,start=0) :
        print(f"下标 {index}  -> {val}")
    # 场景 B：列表推导式数据清洗
    raw_tags = ["AI", "", "Agent", None, "Python", ""]
    # 【TODO 3-2】:
    # 请写一行【列表推导式】，把其中的空字符串 "" 和 None 过滤掉，
    # 只保留有效的数据，期望结果: ['AI', 'Agent', 'Python']
    valid_tags = [v for v in raw_tags if v]  # 请将 None 替换为你的推导式代码: [ ... ]
    print(f"清洗后的有效标签: {valid_tags}")


# ==============================================================================
# 主执行入口
# ==============================================================================
if __name__ == "__main__":
    print("================ 开始答题测试 ================")
    question_one()
    question_two()
    question_three()
    print("==============================================")

