"""
================================================================================
DAY 01 实战源码：Python 现代核心语法与异步并发（前端专属深度对照版）
================================================================================
文件定位：
    帮助具备 JavaScript / TypeScript 背景的开发者快速建立 Python 现代核心心智模型。
    涵盖：列表/字典高频方法深度对比、推导式与迭代器、解包操作符、以及 asyncio 异步模型与 Promise 对照。

运行方式：
    python day01_python_basics.py
"""

import asyncio
import io
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# 适配 Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# 1. 列表 (List) 核心方法与类似方法深度对比
# ==============================================================================
# 前端等价物：JavaScript 的 Array (const arr = [])


def demonstrate_list_methods():
    print("=" * 75)
    print("【1. 列表 (List) 核心方法与类似方法深度对比】")
    print("=" * 75)

    frameworks: List[str] = ["React", "Vue", "Next.js"]

    # --------------------------------------------------------------------------
    # 场景 A：添加元素 —— .append() vs .extend() vs + 拼接
    # --------------------------------------------------------------------------
    # 【方法 1】：list.append(item)
    #   作用：把传入的整个对象当作【单个独立元素】追加到列表末尾（原地修改，无返回值）。
    #   对标 JS：Array.prototype.push(item)
    frameworks.append("FastAPI")
    print(f"1.1 .append('FastAPI') 原地追加单项: {frameworks}")

    # 【类似方法 2】：list.extend(iterable)
    #   作用：把另一个可迭代对象（列表、元组）里的所有元素“拆开散落”逐个追加进去。
    #   对标 JS：arr.push(...otherArr)
    #   与 append 的区别：如果传 ["LangChain", "LlamaIndex"]：
    #     - append 会把整个列表当成一个嵌套子列表加进去: ['React', ..., ['LangChain', ...]]
    #     - extend 会把元素一个个拆解平铺加进去: ['React', ..., 'LangChain', 'LlamaIndex']
    frameworks.extend(["LangChain", "LlamaIndex"])
    print(f"1.2 .extend(['LangChain', 'LlamaIndex']) 平铺展开追加: {frameworks}")

    # 【类似方法 3】：+ 运算符（拼接）
    #   与 append/extend 的区别：
    #     - append/extend 是【原地修改 (In-place)】，不创建新列表，内存性能好；
    #     - + 会【全新分配内存并拷贝】返回一个全新的新列表（对标 JS 的 arr.concat(otherArr)）。
    new_combined = frameworks + ["Docker"]
    print(f"1.3 + 运算符返回全新列表: {new_combined} (原列表不变)")

    # --------------------------------------------------------------------------
    # 场景 B：元素删除 —— .pop() vs .remove() vs del 语句
    # --------------------------------------------------------------------------
    # 【方法 1】：list.pop([index])
    #   作用：按【索引位置】删除，并把被删除的那个元素 return 返回出来（默认删末尾）。
    #   对标 JS：arr.pop() / arr.splice(index, 1)[0]
    removed_last = frameworks.pop()  # 弹出末尾的 "LlamaIndex"
    print(f"1.4 .pop() 按位置弹出并返回值: 弹出了 '{removed_last}', 剩余: {frameworks}")

    # 【类似方法 2】：list.remove(value)
    #   作用：按【元素的值】搜索并删除第一个匹配项（找不到会抛 ValueError 异常！无返回值）。
    #   与 pop 的区别：pop 认“下标位置”，remove 认“内容长什么样”。
    frameworks.remove("Vue")
    print(f"1.5 .remove('Vue') 按内容查找并剔除: {frameworks}")

    # 【类似方法 3】：del list[index]
    #   作用：Python 底层关键字，直接销毁指定下标处的变量指针，不返回值。
    del frameworks[0]  # 删掉第 0 项 "React"
    print(f"1.6 del frameworks[0] 关键字底层删除: {frameworks}")

    # --------------------------------------------------------------------------
    # 场景 C：切片 (Slice) —— [start:stop:step]
    # --------------------------------------------------------------------------
    # 作用：高效截取子数组。对标 JS 的 Array.prototype.slice(start, stop)。
    # 核心语法：左闭右开（包含 start，不包含 stop）。
    tools = ["Search", "Calculator", "Weather", "SQLRunner", "PythonCodeInterpreter"]
    print(f"1.7 切片 tools[1:4]: {tools[1:4]} (获取下标 1, 2, 3)")
    print(f"1.8 逆向切片 tools[-2:]: {tools[-2:]} (获取倒数最后 2 项，智能体提取最新聊天上下文极高频！)")
    print(f"1.9 步长翻转 tools[::-1]: {tools[::-1]} (优雅实现列表倒序，对标 JS 的 [...tools].reverse())")


# ==============================================================================
# 2. 字典 (Dictionary) 核心方法与类似方法深度对比
# ==============================================================================
# 前端等价物：JavaScript 的普通对象 Object / Map (const obj = {})


def demonstrate_dict_methods():
    print("\n" + "=" * 75)
    print("【2. 字典 (Dictionary) 核心方法与类似方法深度对比】")
    print("=" * 75)

    agent_state: Dict[str, Any] = {
        "user_id": "usr_9527",
        "current_step": "calling_tool",
        "retry_count": 0,
        "is_completed": False,
    }

    # --------------------------------------------------------------------------
    # 场景 A：键值读取 —— dict["key"] vs dict.get("key", default)
    # --------------------------------------------------------------------------
    # 【方法 1】：直接下括号访问 dict["key"]
    #   特点：如果 key 存在，读取很快；如果 key 不存在，【直接当场抛出 KeyError 崩溃】！
    #   对标 JS：在 JS 里 obj.unknown 是 undefined 不会崩，但在 Python 里写 dict["unknown"] 会直接崩！
    user_id = agent_state["user_id"]
    print(f"2.1 直接下标读取 (已知必存在时): user_id={user_id}")

    # 【类似方法 2】：dict.get(key, default=None) 🌟【绝对推荐】
    #   作用：安全读取。如果 key 存在则返回其值；如果不存在，【安全返回 None 或指定的默认值】，绝不报错！
    #   对标 JS：obj.unknown ?? "默认值"（类似可选链与空值合并运算符）
    #   与下标访问的区别：极度安全，后端开发中读取请求头、大模型不确定字段时 100% 必须用 .get()。
    tool_name = agent_state.get("tool_name", "无指定工具")
    print(f"2.2 .get('tool_name', '默认值') 安全读取: tool_name={tool_name}")

    # 【类似方法 3】：dict.setdefault(key, default)
    #   作用：“有则取之，无则补之” —— 如果 key 不存在，不仅返回 default，还会【把 default 写入字典中】！
    #   与 get 的区别：get 只读不写；setdefault 如果查不到，会把新键值对原地存进字典里！
    history = agent_state.setdefault("message_history", [])
    history.append("用户：你好")
    print(f"2.3 .setdefault() 查不到则自动填充新列表: {agent_state['message_history']}")

    # --------------------------------------------------------------------------
    # 场景 B：字典遍历 —— .keys() vs .values() vs .items()
    # --------------------------------------------------------------------------
    # 对标 JS：Object.keys(obj) / Object.values(obj) / Object.entries(obj)
    print("2.4 .items() 同时遍历键和值 (元组解包，对标 Object.entries):")
    for key, val in agent_state.items():
        print(f"    -> 键: {key:<16} 值: {val}")


# ==============================================================================
# 3. 推导式 (Comprehension) 与高阶函数对比
# ==============================================================================


def demonstrate_comprehensions():
    print("\n" + "=" * 75)
    print("【3. 推导式 vs JavaScript .map() / .filter() 对比】")
    print("=" * 75)

    scores = [45, 88, 92, 60, 73, 58]

    # --------------------------------------------------------------------------
    # 场景 A：列表推导式 —— [表达式 for 项 in 迭代对象 if 过滤条件]
    # --------------------------------------------------------------------------
    # 对标 JS：scores.filter(s => s >= 60).map(s => `成绩: ${s}分`)
    # 在 Python 中，虽然也有 map() 和 filter() 函数，但官方强烈推荐用推导式，
    # 因为推导式可读性最强，运行速度也比传 lambda 函数给 map/filter 快得多！
    passed_labels = [f"成绩合格: {s}分" for s in scores if s >= 60]
    print(f"3.1 列表推导式 (替代 filter + map): {passed_labels}")

    # --------------------------------------------------------------------------
    # 场景 B：字典推导式 —— {k: v for ... in ...}
    # --------------------------------------------------------------------------
    # 场景：快速把列表转为映射字典，或者过滤字典中的键值对
    raw_users = [("u1", "小陈"), ("u2", "小李"), ("u3", "老王")]
    user_map = {uid: name for uid, name in raw_users if uid != "u2"}
    print(f"3.2 字典推导式快速构建 Map 映射: {user_map}")


# ==============================================================================
# 4. 异步并发核心方法深度对比：asyncio.gather vs asyncio.wait
# ==============================================================================
# 前端等价物：Promise.all([p1, p2]) vs Promise.allSettled vs Promise.race


async def fake_network_io(service_name: str, delay_seconds: float) -> str:
    """模拟异步网络请求"""
    print(f"  [发起请求] -> 正在调用外部服务: {service_name} (模拟延迟 {delay_seconds}s)")
    await asyncio.sleep(delay_seconds)
    print(f"  [调用成功] <- 外部服务 {service_name} 响应完成！")
    return f"【{service_name} 数据】"


async def demonstrate_async_concurrency():
    print("\n" + "=" * 75)
    print("【4. 异步并发模型：asyncio.gather vs asyncio.create_task】")
    print("=" * 75)

    start_time = time.perf_counter()

    # --------------------------------------------------------------------------
    # 方法对比：
    # 1. 串行等待：
    #    res1 = await fake_network_io(...)
    #    res2 = await fake_network_io(...)
    #    总耗时 = 0.8 + 1.2 = 2.0 秒！
    #
    # 2. 并发调度 (asyncio.gather)：
    #    同时把两个协程加入事件循环，总耗时 = 取最大值 max(0.8, 1.2) = 1.2 秒！
    #    严格对标 JavaScript 的 Promise.all([p1, p2])。
    # --------------------------------------------------------------------------
    task1 = fake_network_io("向量知识库 (Chroma)", 0.8)
    task2 = fake_network_io("大模型推理 (DeepSeek)", 1.2)

    # gather 会按传入顺序收集并返回所有结果
    results = await asyncio.gather(task1, task2)

    elapsed = time.perf_counter() - start_time
    print(f"\n4.1 asyncio.gather 并发全部执行完毕！")
    print(f"    实际总耗时: {elapsed:.2f}s (仅取决于最慢的那个，而不是累加！)")
    print(f"    收集到的结果列表: {results}")


# ==============================================================================
# 5. 主函数入口
# ==============================================================================

if __name__ == "__main__":
    # 1. 列表操作与类似方法对比
    demonstrate_list_methods()

    # 2. 字典安全操作与遍历对比
    demonstrate_dict_methods()

    # 3. 列表/字典推导式
    demonstrate_comprehensions()

    # 4. 异步事件循环 (Event Loop) 启动与并发
    # 类似于前端浏览器底层自动常驻的事件循环，Python 脚本入口需通过 asyncio.run() 激活并驱动协程
    asyncio.run(demonstrate_async_concurrency())
