"""
【Python 零基础·课时 01】变量、基本数据类型与 JavaScript / TypeScript 核心对照
文件说明：
    针对前端同学的 Python 第一课！对比 JS 的数据类型，彻底搞懂：
    1. 动态类型与类型注解
    2. Number（整型与浮点型）
    3. String（字符串常用方法与格式化 f-string）
    4. Boolean 与空值（None vs null/undefined）
运行方式：
    python lesson01_variables_and_types.py
"""

# ==============================================================================
# 1. 变量声明与类型注解（对比 JS 中的 let / const 与 TS 类型）
# ==============================================================================
def demo_variables_and_types():
    print("=== 1. 变量与基本数据类型 ===")

    # JS/TS 写法: let age: number = 25; const name: string = "张三";
    # Python 写法: 直接 变量名: 类型 = 值 (不需要 let / const / var)
    age: int = 25
    salary: float = 18500.50
    user_name: str = "小陈"
    is_learning_agent: bool = True  # 注意：首字母必须大写 True / False (不能写小写 true/false)

    # 空值对比：
    # JS 中有 null 和 undefined
    # Python 只有 None (首字母必须大写，表示“无”或“空”)
    current_project: str | None = None  # 类似 TS 的 string | null

    print(f"姓名: {user_name}, 年龄: {age}, 薪资: {salary}")
    print(f"正在学习 Agent: {is_learning_agent}, 当前项目状态: {current_project}")

    # 类型检查：使用 type() 函数，类似 JS 的 typeof
    print(f"age 的实际类型: {type(age)}")      # <class 'int'>
    print(f"salary 的实际类型: {type(salary)}")  # <class 'float'>
    print(f"None 的实际类型: {type(current_project)}") # <class 'NoneType'>


# ==============================================================================
# 2. 字符串常用内置方法（最常用于大模型 Prompt 拼接与文本清理）
# ==============================================================================
def demo_string_methods():
    print("\n=== 2. 字符串常用方法全精讲（对比 JS String API） ===")

    raw_text = "   Hello, AI Agent Developer! Welcome to Python.   "

    # 1. 去除首尾空白字符
    # 类似 JS 的 raw_text.trim()
    clean_text = raw_text.strip()
    print(f"1. .strip() 去除首尾空格: '{clean_text}'")

    # 2. 大小写转换
    # 类似 JS 的 .toLowerCase() 和 .toUpperCase()
    print(f"2. .lower() 转小写: '{clean_text.lower()}'")
    print(f"   .upper() 转大写: '{clean_text.upper()}'")

    # 3. 替换内容
    # 类似 JS 的 .replaceAll("old", "new")
    replaced_text = clean_text.replace("Python", "LangGraph & FastAPI")
    print(f"3. .replace() 文本替换: '{replaced_text}'")

    # 4. 判断开头与结尾（非常高频用于判断大模型返回的 markdown 代码块）
    # 类似 JS 的 .startsWith() 和 .endsWith()
    code_block = "```python\nprint('hello')\n```"
    is_markdown_code = code_block.startswith("```")
    print(f"4. .startswith('```') 判断前缀: {is_markdown_code}")

    # 5. 分割与合并（对标 JS 的 .split() 与 .join()）
    skills_csv = "React,TypeScript,Node.js,Next.js"
    # JS: skills_csv.split(",")
    skill_list = skills_csv.split(",")
    print(f"5. .split(',') 切割为列表: {skill_list}")

    # JS: skill_list.join(" -> ")
    # Python 的 join 语法是 "连接符".join(列表)，这点跟 JS 刚好相反！
    joined_text = " -> ".join(skill_list)
    print(f"   '连接符'.join(列表) 合并: {joined_text}")

    # 6. 核心法宝：f-string 格式化字符串
    # 类似 JS ES6 的模板字符串 `${var}`
    role = "前端工程师"
    target = "AI Agent 架构师"
    # 注意字符串前面的小写 'f'，大括号内直接嵌入表达式
    message = f"【个人宣言】: 我是一名拥有扎实基础的 {role}，立志转型为顶尖的 {target}！"
    print(f"6. f-string 模板字符串: {message}")


# ==============================================================================
# 3. 数字运算与逻辑操作符对比
# ==============================================================================
def demo_operators():
    print("\n=== 3. 常用操作符与 JS 差异对比 ===")

    # 1. 除法与整除
    # JS 中 5 / 2 = 2.5，需要 Math.floor(5 / 2) 才能取整
    # Python 中:
    #   /   普通浮点除法
    #   //  整除（向下取整，直接相当于 Math.floor）
    #   %   取模/求余数
    #   **  乘方 (相当于 JS 的 Math.pow 或 ** )
    print(f"普通除法 7 / 2 = {7 / 2}")    # 3.5
    print(f"整除取整 7 // 2 = {7 // 2}")  # 3 (相当于 Math.floor(7 / 2))
    print(f"乘方 2 ** 3 = {2 ** 3}")      # 8 (2 的 3 次方)

    # 2. 逻辑运算符（Python 不使用 &&, ||, !，而是使用纯英文单词！）
    # JS: a && b    ===> Python: a and b
    # JS: a || b    ===> Python: a or b
    # JS: !a        ===> Python: not a
    has_token = True
    is_expired = False

    can_access = has_token and (not is_expired)
    print(f"逻辑运算 (has_token and not is_expired): {can_access}")


if __name__ == "__main__":
    demo_variables_and_types()
    demo_string_methods()
    demo_operators()
