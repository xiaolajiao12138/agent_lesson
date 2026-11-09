"""
【Python 零基础·课时 06】异常处理机制与文件读写（with 语法糖）
文件说明：
    智能体在调用网络 API 或解析本地文件时，经常会遇到网络波动、JSON 损坏或文件缺失。
    本文件详解：
    1. try...except...else...finally 结构（对标 JS try...catch...finally）
    2. with open(...) as f 上下文管理器（为什么再也不用担心文件句柄泄露）
运行方式：
    python lesson06_exceptions_and_file_io.py
"""

import json
import os

# ==============================================================================
# 1. 异常处理结构（对标 JS try...catch...finally）
# ==============================================================================
def demo_exception_handling():
    print("=== 1. 异常捕获机制全解析 ===")

    # JS 写法：
    # try { ... } catch (err) { ... } finally { ... }

    # Python 写法：
    # try:
    #     可能出错的代码
    # except SpecificError as e:  # 捕获特定类型的错误
    #     处理逻辑
    # except Exception as e:      # 兜底捕获所有未知错误 (类似 catch(err))
    #     处理逻辑
    # else:                       # 核心差异：如果没有发生任何异常时执行！
    #     正常完成的逻辑
    # finally:                    # 无论成功或失败，一定会执行的清理逻辑
    #     释放资源

    mock_llm_json_output = '{"model": "gpt-4o", "temperature": 0.7'  # 故意缺少闭合括号，模拟大模型生成残缺 JSON

    try:
        print("正在尝试解析大模型返回的 JSON 数据...")
        data = json.loads(mock_llm_json_output)
        print("解析成功:", data)
    except json.JSONDecodeError as err:
        # 精确捕获 JSON 解析错误
        print(f"[捕获到预期错误] 大模型返回了非法的 JSON 格式:\n   原因: {err}")
    except Exception as err:
        # 兜底捕获其他所有异常
        print(f"[捕获到未知异常]: {err}")
    else:
        print("[无异常执行] JSON 数据验证完全合规！")
    finally:
        print("[Finally 清理] 无论如何都会执行（常用于关闭数据库连接/重置 Loading 状态）")


# ==============================================================================
# 2. 文件 I/O 与 with 上下文管理器
# ==============================================================================
def demo_file_io():
    print("\n=== 2. 文件读写与 with 语法糖 ===")

    # 获取当前 py 脚本所在的绝对目录，确保文件必定生成在当前 phase00-python-zero-basis 文件夹下
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "test_agent_memory.txt")

    # 传统不推荐的做法：
    # f = open(file_path, "w")
    # f.write(...)
    # f.close() # 如果中间报错，这行就不会执行，导致文件被长期占用锁死！

    # ✅ 现代 Python 统一规范：使用 with 关键字（上下文管理器）
    # 类似前端的自动资源释放：with 代码块执行完毕后，无论正常结束还是抛出异常，
    # Python 都会 100% 自动调用 f.close() 关闭文件！
    
    # 1. 覆盖写入（"w" 模式：如果文件已存在，会彻底清空后重新写）
    # 1. 写入文件（"w" 覆盖写入模式）
    # encoding="utf-8" 极其重要，防止 Windows 中文乱码！
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# 智能体持久化记忆存储\n")
        f.write("用户偏好：喜欢使用 TypeScript 和 Next.js。\n")
        f.write("学习目标：2026 年转型 AI 智能体开发。\n")
    print(f"1. 成功使用 'w' 模式覆盖写入文件: {file_path}")

    # 2. 追加写入（"a" 模式：保留旧内容，在文件末尾接着追加）
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("追加记录：已完成 Python 异常捕获与文件操作学习！\n")
    print(f"2. 成功使用 'a' 模式追加新行")
    print(f"1. 成功使用 with open ('w' 模式) 覆盖写入文件: {file_path}")

    # 2. 追加写入文件（"a" append 追加模式：保留原有内容，向末尾追加）
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("新增记忆：用户正在学习文件追加写入（'a' 模式）。\n")
        f.write("系统响应：已成功在原有记忆末尾追加了两条最新记录！\n")
    print(f"2. 成功使用 with open ('a' 模式) 追加新内容到文件")

    # 3. 读取文件（"r" 只读模式）
    with open(file_path, "r", encoding="utf-8") as f:
        # .read() 读取全部内容
        # .readlines() 按行读取返回列表
        content = f.read()
    print(f"3. 成功读取合并后的完整文件内容:\n---\n{content.strip()}\n---")
    print(f"3. 成功读取完整文件内容（包含覆盖写入与追加内容）:\n---\n{content.strip()}\n---")

    # 清理测试生成的临时文件
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"已清理临时测试文件: {file_path}")

    # 【真实保留文件】：为了让你在左侧文件列表能亲眼点开查看，这里不删除文件
    print(f"\n[真实文件已生成并保留]: {file_path}")
    print("你可以直接在左侧文件列表中点击 'test_agent_memory.txt' 查看内容！")

    if os.path.exists(file_path) :
        os.remove(file_path)
if __name__ == "__main__":
    demo_exception_handling()
    demo_file_io()
