"""
【Python 零基础·课时 04】函数传参精讲、*args 与 **kwargs（对标 JS 解构 rest）
文件说明：
    在 Agent 开发中，工具函数的参数千奇百怪。
    你经常会看到 def my_tool(*args, **kwargs) 这种写法。
    本文件用 JS 的对象解构和剩余参数（...rest）全面对照解释。
运行方式：
    python lesson04_functions_args_kwargs.py
"""

from typing import List, Callable, Any

# ==============================================================================
# 1. 基础函数与关键字传参（Keyword Arguments）
# ==============================================================================

# 在 JS 中：function createPrompt(user, system = "默认角色") {...}
# 调用时 JS 只能按位置传参，或者传一个配置对象 { user, system }
# 而在 Python 中：原生支持指定形参名称传参！
def generate_prompt(user_input: str, system_role: str = "通用助手", temperature: float = 0.7) -> str:
    """构建提示词的标准函数"""
    return f"[系统人设: {system_role} | 温度: {temperature}] -> 用户输入: {user_input}"

def demo_keyword_args():
    print("=== 1. 位置传参 vs 关键字传参 ===")
    
    # 方式 A：纯位置传参（和 JS 完全一样）
    p1 = generate_prompt("你好", "代码专家", 0.2)
    print(f"位置传参结果:\n   {p1}")

    # 方式 B：关键字传参（可以完全打乱顺序，可读性极高！）
    # 在 Agent 调度工具时，绝大多数时候都是把解析出来的 JSON 参数解构成关键字参数传入
    p2 = generate_prompt(
        temperature=0.0,
        user_input="分析这段 SQL",
        system_role="数据库 DBA"
    )
    print(f"关键字传参结果:\n   {p2}")


# ==============================================================================
# 2. *args 与 **kwargs：彻底解密 Python 的动态传参
# ==============================================================================
# 对标 JavaScript：
# 1. *args   <====> JS 函数参数中的剩余数组 function fn(...args)
#    它会把多余传入的位置参数打包为一个【元组 Tuple】
# 2. **kwargs <====> JS 中的配置项对象扩展 function fn({ ...options })
#    它会把多余传入的形如 key=value 的关键字参数打包为一个【字典 Dict】

def flexible_agent_executor(agent_name: str,name:str, *args, **kwargs):
    """
    一个可以接收任意数量位置参数和任意键值对的通用智能体执行器
    """
    print(f"\n[智能体调度器] 正在启动智能体: {agent_name}")
    print(f"   捕获到的多余位置参数 *args: {args} (类型: {type(args)})")
    print(f"   捕获到的关键字参数 **kwargs: {kwargs} (类型: {type(kwargs)})")
    print(f" 打印'张三'，{name}")
    # 可以从 kwargs 中提取特定的配置参数
    max_retries = kwargs.get("max_retries", 3)
    verbose = kwargs.get("verbose", False)
    print(f"   解析内部配置: 最大重试={max_retries}, 调试模式={verbose}")

def demo_args_kwargs():
    print("\n=== 2. *args 和 **kwargs 实战 ===")
    
    # 调用时传入了 1 个固定参数，2 个额外位置参数，3 个额外关键字参数
    flexible_agent_executor(
        "CodeReviewAgent",
        'zhangsan',
        '李四',
        "doc_01.py", "doc_02.py",          # 进去变成 *args = ('doc_01.py', 'doc_02.py')
        max_retries=5,
        verbose=True,
        environment="staging",              # 进去变成 **kwargs = {'max_retries': 5, 'verbose': True, 'environment': 'staging'}
    )

    # 逆向解包传参（对标 JS 的 fn(...array) 和 fn({ ...object })）
    tool_args_dict = {"temperature": 0.5, "system_role": "测试工程师", "user_input": "编写单元测试"}
    # 使用 ** 直接把字典解构为函数的形参传入！
    # 类似 JS: generate_prompt(...Object.values(tool_args_dict))
    result = generate_prompt(**tool_args_dict)
    print(f"\n使用 ** 解构字典传参:\n   {result}")


# ==============================================================================
# 3. 匿名函数 lambda 与高阶函数（对标 JS 箭头函数 (x) => x * 2）
# ==============================================================================
def demo_lambda():
    print("\n=== 3. 匿名函数 lambda (对标 JS 箭头函数) ===")

    # JS: const add = (a, b) => a + b;
    # Python: add = lambda a, b: a + b
    add: Callable[[int, int], int] = lambda a, b: a + b
    print(f"lambda 运算 10 + 20 = {add(10, 20)}")

    # 常见应用：给复杂列表做排序
    # 类似 JS: toolList.sort((a, b) => a.priority - b.priority)
    tools = [
        {"name": "web_search", "priority": 3},
        {"name": "code_sandbox", "priority": 1},
        {"name": "file_reader", "priority": 2}
    ]
    # key 参数接收一个函数，提取排序指标
    newtools = tools.sort(key=lambda item: item["priority"])
    print(f"按优先级升序排序后: {tools}")

    # ==========================================================================
    # 4. 高阶函数实战：使用 Callable 将函数作为参数传入
    # ==========================================================================
    def run_agent_step(query: str, tool: Callable[[str], str]) -> str:
        """tool 必须是一个接收 string 并返回 string 的可调用函数"""
        result = tool(query)
        return f"智能体执行结果: {result}"

    # 定义一个具体的工具函数（普通 def 函数）
    def search_weather(city: str) -> str:
        return f"{city}天气晴朗，气温 25°C"

    # 调用方式 A：传入普通函数名（注意只传名字，不加括号！）
    output_normal = run_agent_step("北京", search_weather)
    print(f"\n[高阶函数调用] 具名函数: {output_normal}")

    # 调用方式 B：传入 lambda 匿名函数（轻量逻辑一行搞定）
    output_lambda = run_agent_step("hello agent", lambda text: text.upper())
    print(f"[高阶函数调用] lambda 函数: {output_lambda}")


if __name__ == "__main__":
    demo_keyword_args()
    demo_args_kwargs()
    demo_lambda()



from typing import Callable

# 1. 这是接收函数的“执行器”
def run_agent_step(query: str, tool: Callable[[str], str]) -> str:
    # 此时 tool 是一个函数，我们给它加上括号 () 传入 query 执行
    result = tool(query)
    return f"智能体执行结果: {result}"


# ==========================================
# 调用方式 1：传入一个定义好的普通函数（最常用）
# ==========================================
def search_weather(city: str) -> str:
    """具体的查天气工具函数"""
    return f"{city}的天气为【晴天，气温 23°C】"

# ⚠️ 注意传参细节：只写函数名 search_weather，千万不要加括号！
output1 = run_agent_step("深圳", search_weather)
print(output1)
# 打印: 智能体执行结果: 深圳的天气为【晴天，气温 23°C】


# ==========================================
# 调用方式 2：直接传入 lambda 匿名函数（轻量临时工具）
# ==========================================
# 类似前端直接写箭头函数: (text) => text.toUpperCase()
output2 = run_agent_step(
    "hello agent", 
    lambda text: text.upper()
)
print(output2)
# 打印: 智能体执行结果: HELLO AGENT


# ==========================================
# 常见翻车现场（反面教材）
# ==========================================
# ❌ 错误 1：不小心传了字符串
# run_agent_step("北京", "search_weather")  
# 报错: TypeError: 'str' object is not callable（字符串不能加括号调用！）

# ❌ 错误 2：传参时不小心加了括号
# run_agent_step("北京", search_weather("北京")) 
# 报错！因为 search_weather("北京") 会先执行并返回一个字符串，导致 tool 又变成了字符串！