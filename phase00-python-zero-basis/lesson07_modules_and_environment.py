"""
【Python 零基础·课时 07】模块导入规范与彻底搞懂 if __name__ == '__main__'
文件说明：
    1. 模块导入机制：import 与 from...import（对标 ES6 import）
    2. 终极解密：为什么每个 Python 文件底部都要写 if __name__ == '__main__'？
    3. 虚拟环境（venv）与极速包管理器 uv 的正确打开方式。
运行方式：
    python lesson07_modules_and_environment.py
"""

# ==============================================================================
# 1. 模块导入与 JavaScript ES Module 对照
# ==============================================================================

# JS: import os from 'os';
import os

# JS: import { basename, join as joinPath } from 'path';
from os.path import basename, join as join_path

# JS: import * as mathUtils from './math';
import math

def demo_module_import():
    print("=== 1. 模块导入语法对照 ===")
    
    # 使用导入的函数
    current_file = basename(__file__) # 获取当前执行的脚本文件名
    print(f"当前文件名: {current_file}")
    
    combined_path = join_path("workspace", "agent_project", "main.py")
    print(f"跨平台安全拼接路径: {combined_path}")

    print(f"调用 math 模块计算圆周率: {math.pi:.4f}")


# ==============================================================================
# 2. 彻底搞懂：if __name__ == '__main__'
# ==============================================================================

# 【常见困惑】前端同学第一眼看到这个往往一头雾水：
# 这是什么晦涩的密码？为什么要写这个奇怪的 if 判断？

# 【大白话解释】：
# 1. 在 Python 中，每个 .py 文件都有一个内置全局变量叫做 `__name__`。
# 2. 如果你是直接在终端输入 `python lesson07_modules_and_environment.py` 运行该文件，
#    Python 解释器会自动把该文件的 `__name__` 变量赋值为字符串 `"__main__"`。
# 3. 如果这个文件是被另外一个文件通过 `import lesson07_modules_and_environment` 导入的，
#    那么这个文件的 `__name__` 就会是该模块的名字 `"lesson07_modules_and_environment"`，而不是 `"__main__"`！

# 【结论】：
# 写 `if __name__ == '__main__':` 的目的，就是为了保证：
# 只有在直接手动运行这个文件进行测试时，下面的代码才会执行；
# 而当别人 import 这个文件里的函数和类时，下面的测试代码不会被意外触发执行！

def run_standalone_test():
    print("\n=== 2. if __name__ == '__main__' 运行结果 ===")
    print(f"当前文件的 __name__ 变量值为: '{__name__}'")
    print("-> 因为你在终端直接运行了本文件，所以条件成立，本测试逻辑被成功触发！")


# ==============================================================================
# 3. 终端命令清单：如何创建与管理虚拟环境
# ==============================================================================

ENVIRONMENT_GUIDE = """
=== 3. 为什么必须用虚拟环境（venv）？===
在前端中，每个项目都有独立的 node_modules，依赖不会互相污染。
但传统的 Python 默认会把 pip 包安装在全局操作系统里！
如果项目 A 依赖 langchain 0.1，项目 B 依赖 langchain 0.2，全局就会产生灾难性的版本冲突。

因此，每个 Agent 项目第一步必须创建虚拟环境（相当于创建当前项目的 node_modules）：

1. 创建虚拟环境目录（只需运行一次）：
   python -m venv .venv

2. 激活虚拟环境：
   - Windows PowerShell:
     .venv\\Scripts\\Activate.ps1
   - Mac / Linux:
     source .venv/bin/activate
   （激活后，你的终端提示符最前面会出现 (.venv) 标记）

3. 在虚拟环境中安全安装依赖：
   pip install openai pydantic fastapi uvicorn
"""

if __name__ == "__main__":
    demo_module_import()
    run_standalone_test()
    print(ENVIRONMENT_GUIDE)
