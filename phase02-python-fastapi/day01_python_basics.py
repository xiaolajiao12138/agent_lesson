"""
DAY 01 实战源码：Python 现代核心语法与异步并发（前端专属对照版）
文件说明：帮助前端开发者在 15 分钟内掌握 Python 核心语法，对照 JS/TS 理解变量、解构、字典、列表推导式与 asyncio 异步模型。
运行方式：python day01_python_basics.py
"""

import asyncio
import time
from typing import List, Dict, Optional, Tuple, Any

# ==============================================================================
# 1. 基础数据结构与 TypeScript / JavaScript 概念映射
# ==============================================================================

def demonstrate_data_structures():
    print("=== 1. 核心数据结构与 TS 对照 ===")
    
    # 列表 (List) <---> JS 的 Array
    # 支持 push 对应 append，pop 对应 pop，切片 slice
    frameworks: List[str] = ["React", "Vue", "Next.js"]
    frameworks.append("FastAPI") # 类似 JS 的 frameworks.push("FastAPI")
    print(f"前端框架列表: {frameworks}")
    print(f"切片获取前两个元素 (类似 .slice(0, 2)): {frameworks[0:2]}")

    # 字典 (Dictionary) <---> JS 的 Object / Record<string, any>
    # 键值对映射，访问使用 dict["key"] 或 dict.get("key", 默认值)
    developer: Dict[str, Any] = {
        "name": "Alex",
        "original_stack": "Frontend (TypeScript/React)",
        "target_stack": "AI Agent Engineer",
        "years_of_experience": 4
    }
    # 使用 .get() 可以防止像 JS 访问 undefined 属性引发报错的情况
    hobby = developer.get("hobby", "写代码与探索大模型")
    print(f"开发者信息: {developer['name']}, 目标方向: {developer['target_stack']}, 爱好: {hobby}")

    # 列表推导式 (List Comprehension) <---> JS 的 .map() 和 .filter()
    # 语法：[表达式 for 项 in 迭代对象 if 条件]
    numbers = [1, 2, 3, 4, 5, 6]
    # 类似 JS: numbers.filter(n => n % 2 === 0).map(n => n * 10)
    doubled_evens = [n * 10 for n in numbers if n % 2 == 0]
    print(f"偶数放大十倍 (类似 filter+map): {doubled_evens}")


# ==============================================================================
# 2. 异步编程模型：Python asyncio 与 JS Promise / async-await 对照
# ==============================================================================
# 在 JS 中，Promise 直接在微任务队列执行；
# 在 Python 中，async def 会创建一个协程对象 (Coroutine)，必须通过 await 或调度器主动驱动。

async def fetch_llm_response(mock_provider: str, delay_seconds: float) -> str:
    """
    模拟调用大模型 API 的异步等待函数
    
    参数:
        mock_provider (str): 大模型供应商名称，例如 'OpenAI' 或 'DeepSeek'
        delay_seconds (float): 模拟网络与模型推理延迟的秒数
    返回:
        str: 模型返回的文本结果
    """
    print(f"-> 开始请求大模型 [{mock_provider}] ...")
    # asyncio.sleep 对应前端的 await new Promise(resolve => setTimeout(resolve, ms))
    await asyncio.sleep(delay_seconds)
    print(f"<- 大模型 [{mock_provider}] 推理完成！耗时: {delay_seconds}s")
    return f"来自 {mock_provider} 的分析报告：任务规划合理，准予执行。"

async def run_concurrent_tasks():
    print("\n=== 2. 异步并发调用 (类似 Promise.all) ===")
    start_time = time.time()

    # 模拟同时向两个不同模型厂商（例如同时查两个 Agent 节点）发起异步请求
    # asyncio.gather 严格等价于 JavaScript 中的 Promise.all([task1, task2])
    task_openai = fetch_llm_response("OpenAI-GPT4o", 1.5)
    task_deepseek = fetch_llm_response("DeepSeek-R1", 1.2)

    # 并发等待两个协程执行
    results = await asyncio.gather(task_openai, task_deepseek)

    total_cost_time = time.time() - start_time
    print(f"并发请求全部完成，总耗时仅需（取最大耗时）: {total_cost_time:.2f} 秒")
    for res in results:
        print(f"返回数据快照: {res}")

# ==============================================================================
# 3. 主函数入口（Python 的标准启动规范）
# ==============================================================================

if __name__ == "__main__":
    # 1. 演示基础结构
    demonstrate_data_structures()

    # 2. 启动异步事件循环 (Event Loop)
    # 类似于前端浏览器自动管理的全局 Event Loop，在 Python 脚本中用 asyncio.run() 开启
    asyncio.run(run_concurrent_tasks())
