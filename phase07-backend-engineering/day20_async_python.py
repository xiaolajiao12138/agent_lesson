"""
================================================================================
DAY 20 实战源码：Python 异步编程详解（asyncio 全家桶 + 异步调用大模型）
================================================================================
配套讲义：daily_lessons/DAY_20_Python异步编程详解.md

本文件包含 10 个可独立运行的演示，每个演示都会打印耗时，让你亲眼看到差别：
    1. 协程是“懒”的：忘记 await 会发生什么
    2. 串行 await vs create_task 并发
    3. gather vs gather(return_exceptions=True) vs TaskGroup（失败处理差异）
    4. as_completed vs wait(FIRST_COMPLETED)（谁快用谁）
    5. timeout vs wait_for（超时控制）
    6. Semaphore（限制并发数，防止被接口限流）
    7. time.sleep vs asyncio.sleep vs to_thread（阻塞代码的危害与解法）
    8. 异步生成器 + async for（SSE 流式推送的底层原理）
    9. httpx.AsyncClient（异步 HTTP 请求）
   10. AsyncOpenAI 真实并发调用大模型（需要 .env 配置，可选）

前端概念镜像对照：
    - async def / await           <=====> async function / await
    - asyncio.gather              <=====> Promise.all
    - gather(return_exceptions)   <=====> Promise.allSettled
    - asyncio.wait(FIRST_COMPLETED) <===> Promise.race
    - asyncio.Semaphore           <=====> p-limit
    - async def + yield / async for <===> async function* / for await

运行方式：
    python day20_async_python.py          # 运行全部离线演示（不消耗 Token）
    python day20_async_python.py --llm    # 额外运行第 10 个真实大模型演示
"""

import asyncio
import os
import sys
import time

# ==============================================================================
# 工具函数：模拟一个“需要等待”的异步操作（比如调用大模型 / 搜索接口）
# ==============================================================================


async def fake_llm_call(name: str, delay: float, should_fail: bool = False) -> str:
    """
    模拟一次大模型调用。

    参数：
        name: 模型或工具的名字，方便在日志里区分
        delay: 模拟网络 + 推理耗时（秒）
        should_fail: 为 True 时模拟接口报错
    """
    print(f"    [开始] {name}（预计 {delay}s）")
    try:
        # asyncio.sleep 是“异步等待”：等待期间会把控制权交还给事件循环，
        # 事件循环可以趁机去执行其他协程。这就是并发的来源。
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        # 当任务被取消时（例如 TaskGroup 中其他任务失败），这里会收到 CancelledError
        print(f"    [被取消] {name}")
        raise  # ⚠️ 必须重新抛出，否则取消机制会失效

    if should_fail:
        raise RuntimeError(f"{name} 接口返回 500 错误")
    print(f"    [完成] {name}")
    return f"{name} 的回答"


def title(text: str) -> None:
    """打印每个演示的标题分隔线"""
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


# ==============================================================================
# 演示 1：协程是“懒”的
# ==============================================================================
# 与 JS 最大的不同：JS 调用 async 函数时立刻开始执行；
# Python 调用 async 函数只会得到一个“协程对象”，必须 await 才会执行。


async def demo_lazy_coroutine():
    title("演示 1：协程是“懒”的 —— 调用 async 函数 ≠ 执行它")

    coro = fake_llm_call("懒协程", 0.1)
    # 此时控制台不会打印 [开始]，因为函数体根本没有运行
    print(f"  调用后拿到的是：{coro!r}")
    print(f"  它的类型是：{type(coro).__name__}")

    # 只有 await 之后才真正执行
    result = await coro
    print(f"  await 之后拿到的才是结果：{result}")

    # 💡 如果你只写 fake_llm_call(...) 而不 await，Python 会在垃圾回收时提示：
    #    RuntimeWarning: coroutine 'fake_llm_call' was never awaited


# ==============================================================================
# 演示 2：串行 await vs create_task 并发
# ==============================================================================


async def demo_serial_vs_concurrent():
    title("演示 2：串行 await vs create_task 并发")

    # ---------- 写法 A：连续 await（串行）----------
    print("  ▶ 写法 A：连续 await —— 一个做完才开始下一个")
    start = time.perf_counter()
    a = await fake_llm_call("GPT", 1.0)
    b = await fake_llm_call("DeepSeek", 1.0)
    print(f"  串行耗时：{time.perf_counter() - start:.2f}s（≈ 1 + 1）")

    # ---------- 写法 B：先 create_task 再 await（并发）----------
    # create_task 会立刻把协程交给事件循环“开始跑”，返回一个 Task 对象。
    # 类似 JS 里先调用 const p = fetch() 不 await，稍后再 await p。
    print("\n  ▶ 写法 B：create_task —— 同时开始，稍后取结果")
    start = time.perf_counter()
    task_a = asyncio.create_task(fake_llm_call("GPT", 1.0))
    task_b = asyncio.create_task(fake_llm_call("DeepSeek", 1.0))
    a = await task_a
    b = await task_b
    print(f"  并发耗时：{time.perf_counter() - start:.2f}s（≈ max(1, 1)）")
    print(f"  结果：{a} / {b}")


# ==============================================================================
# 演示 3：gather / gather(return_exceptions=True) / TaskGroup 的失败处理差异
# ==============================================================================


async def demo_gather_vs_taskgroup():
    title("演示 3：gather vs return_exceptions vs TaskGroup —— 有一个失败时的区别")

    # ---------- 3.1 gather：等价于 Promise.all ----------
    print("  ▶ 3.1 asyncio.gather（≈ Promise.all）")
    print("    特点：按传入顺序返回结果；遇到第一个异常立即抛出，但其他任务不会被取消")
    try:
        results = await asyncio.gather(
            fake_llm_call("搜索工具", 0.5),
            fake_llm_call("天气工具", 0.2, should_fail=True),
            fake_llm_call("计算器", 0.8),
        )
        print(f"    结果：{results}")
    except RuntimeError as err:
        print(f"    ❌ 捕获到异常：{err}")
    # 注意：异常抛出后，“搜索工具”和“计算器”仍在后台继续跑，这里稍等让它们打印完
    await asyncio.sleep(0.8)

    # ---------- 3.2 gather(return_exceptions=True)：等价于 Promise.allSettled ----------
    print("\n  ▶ 3.2 gather(return_exceptions=True)（≈ Promise.allSettled）")
    print("    特点：不抛异常，异常对象直接放进结果列表，由你自己判断")
    results = await asyncio.gather(
        fake_llm_call("向量检索", 0.3),
        fake_llm_call("关键词检索", 0.1, should_fail=True),
        fake_llm_call("知识图谱检索", 0.2),
        return_exceptions=True,
    )
    for r in results:
        if isinstance(r, Exception):
            print(f"    ⚠️ 这一路失败了：{r}")
        else:
            print(f"    ✅ 这一路成功：{r}")

    # ---------- 3.3 TaskGroup：结构化并发（Python 3.11+）----------
    print("\n  ▶ 3.3 asyncio.TaskGroup（Python 3.11+，结构化并发）")
    print("    特点：任意一个失败 → 自动取消组内其他任务 → 抛出 ExceptionGroup")
    try:
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(fake_llm_call("写数据库", 1.0))
            t2 = tg.create_task(fake_llm_call("发邮件", 0.2, should_fail=True))
            t3 = tg.create_task(fake_llm_call("写日志", 1.0))
        # 只有全部成功才会走到这里
        print(f"    结果：{t1.result()}, {t2.result()}, {t3.result()}")
    except* RuntimeError as eg:
        # except* 是 3.11 新语法，专门用来捕获 ExceptionGroup 里的某类异常
        for err in eg.exceptions:
            print(f"    ❌ TaskGroup 捕获到：{err}")
    print("    👉 对比 3.1：这里“写数据库”和“写日志”被取消了，不会留下半截数据")


# ==============================================================================
# 演示 4：as_completed vs wait(FIRST_COMPLETED)
# ==============================================================================


async def demo_as_completed_and_wait():
    title("演示 4：as_completed（按完成顺序处理） vs wait（只要最快的）")

    # ---------- 4.1 as_completed：谁先完成先处理谁 ----------
    print("  ▶ 4.1 asyncio.as_completed —— 谁先回来先展示谁")
    start = time.perf_counter()
    coros = [
        fake_llm_call("慢模型", 1.2),
        fake_llm_call("快模型", 0.3),
        fake_llm_call("中模型", 0.7),
    ]
    for next_done in asyncio.as_completed(coros):
        result = await next_done
        print(f"    → {time.perf_counter() - start:.2f}s 时拿到：{result}")

    # ---------- 4.2 wait(FIRST_COMPLETED)：≈ Promise.race ----------
    print("\n  ▶ 4.2 asyncio.wait(return_when=FIRST_COMPLETED)（≈ Promise.race）")
    print("    场景：同一个问题同时问 3 个模型，用最快的那个，其余取消省钱")
    tasks = [
        asyncio.create_task(fake_llm_call("线路A", 0.9)),
        asyncio.create_task(fake_llm_call("线路B", 0.4)),
        asyncio.create_task(fake_llm_call("线路C", 0.6)),
    ]
    # wait 只接受 Task / Future，不接受裸协程，所以要先 create_task
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    winner = done.pop()
    print(f"    🏆 最快的结果：{winner.result()}")
    for t in pending:
        t.cancel()  # 取消剩下的
    # 等待被取消的任务真正结束（return_exceptions 防止 CancelledError 抛出来）
    await asyncio.gather(*pending, return_exceptions=True)


# ==============================================================================
# 演示 5：超时控制 timeout vs wait_for
# ==============================================================================


async def demo_timeout():
    title("演示 5：超时控制 asyncio.timeout vs asyncio.wait_for")

    # ---------- 5.1 asyncio.timeout：包住一整段代码（3.11+ 推荐）----------
    print("  ▶ 5.1 async with asyncio.timeout(秒) —— 可以包住多行代码")
    try:
        async with asyncio.timeout(1.0):
            await fake_llm_call("第一步：检索", 0.4)
            await fake_llm_call("第二步：生成", 0.9)  # 0.4 + 0.9 > 1.0，会超时
    except TimeoutError:
        print("    ⏰ 整段流程超过 1 秒，被中断")

    # ---------- 5.2 asyncio.wait_for：只能包一个协程（老写法）----------
    print("\n  ▶ 5.2 await asyncio.wait_for(协程, 秒) —— 只能包一个")
    try:
        await asyncio.wait_for(fake_llm_call("超慢模型", 2.0), timeout=0.5)
    except TimeoutError:
        print("    ⏰ 单个调用超过 0.5 秒，被取消")

    # 💡 Python 3.11 起 asyncio.TimeoutError 就是内置的 TimeoutError，两者等价


# ==============================================================================
# 演示 6：Semaphore 限制并发数
# ==============================================================================


async def demo_semaphore():
    title("演示 6：asyncio.Semaphore —— 限制同时进行的请求数（≈ p-limit）")

    # 场景：有 6 段文本要做 Embedding，但接口规定同时最多 3 个请求
    sem = asyncio.Semaphore(3)

    async def embed(idx: int) -> str:
        async with sem:  # 满 3 个时，第 4 个会在这里排队等待
            return await fake_llm_call(f"Embedding-{idx}", 0.5)

    start = time.perf_counter()
    results = await asyncio.gather(*(embed(i) for i in range(1, 7)))
    cost = time.perf_counter() - start
    print(f"  6 个任务、并发上限 3、每个 0.5s → 耗时 {cost:.2f}s（≈ 2 批 × 0.5s）")
    print(f"  结果数量：{len(results)}")


# ==============================================================================
# 演示 7：time.sleep vs asyncio.sleep vs asyncio.to_thread
# ==============================================================================


def blocking_pdf_parse(name: str) -> str:
    """模拟一个只有同步版本的库函数（比如某些 PDF 解析库），内部会阻塞 0.5 秒"""
    time.sleep(0.5)
    return f"{name} 解析完成"


async def heartbeat():
    """心跳协程：每 0.1 秒打印一次。如果事件循环被阻塞，心跳就会停住"""
    for i in range(6):
        print(f"      💓 心跳 {i}")
        await asyncio.sleep(0.1)


async def demo_blocking_vs_to_thread():
    title("演示 7：在 async 里调用阻塞代码的危害，以及 to_thread 解法")

    # ---------- 7.1 错误示范：async 函数里直接调用阻塞函数 ----------
    print("  ▶ 7.1 ❌ 直接调用 blocking_pdf_parse —— 心跳会卡住 0.5 秒")

    async def bad():
        return blocking_pdf_parse("合同.pdf")  # 整个事件循环被冻结

    start = time.perf_counter()
    await asyncio.gather(heartbeat(), bad())
    print(f"    耗时 {time.perf_counter() - start:.2f}s（心跳在解析期间完全停止）")

    # ---------- 7.2 正确示范：用 to_thread 丢进线程池 ----------
    print("\n  ▶ 7.2 ✅ await asyncio.to_thread(...) —— 心跳不受影响")
    start = time.perf_counter()
    await asyncio.gather(
        heartbeat(),
        asyncio.to_thread(blocking_pdf_parse, "合同.pdf"),
    )
    print(f"    耗时 {time.perf_counter() - start:.2f}s（解析与心跳同时进行）")

    # 💡 to_thread 适合 I/O 阻塞（网络、磁盘）；
    #    纯 CPU 计算（如大量数学运算）应该用 loop.run_in_executor + ProcessPoolExecutor


# ==============================================================================
# 演示 8：异步生成器 + async for（SSE 流式推送的底层原理）
# ==============================================================================


async def token_stream(text: str):
    """
    异步生成器：async def 里出现 yield，就变成了“异步生成器”。
    对标 JS 的 async function*。
    FastAPI 的 StreamingResponse 接收的正是这种对象。
    """
    for ch in text:
        await asyncio.sleep(0.05)  # 模拟大模型逐个吐 token
        yield ch


async def demo_async_generator():
    title("演示 8：异步生成器 async def + yield，配合 async for 消费")

    print("  ▶ 逐字打印（这就是打字机效果的本质）：", end="", flush=True)
    async for token in token_stream("你好，我是异步生成器！"):
        print(token, end="", flush=True)
    print()

    # 对比三种“生成器 / 迭代”写法：
    # 1. def + yield            → 同步生成器，用 for 遍历
    # 2. async def + yield      → 异步生成器，用 async for 遍历
    # 3. async def + return     → 普通协程，用 await 拿一次性结果
    # ⚠️ async 生成器里不能写 return 值（只能写空的 return），想返回结果请 yield 出去


# ==============================================================================
# 演示 9：httpx.AsyncClient 异步 HTTP 请求
# ==============================================================================


async def demo_httpx():
    title("演示 9：httpx.AsyncClient —— 异步版的 requests")

    try:
        import httpx
    except ImportError:
        print("  未安装 httpx，执行 pip install httpx 后再试")
        return

    # async with 会在结束时自动关闭连接池（类似 with open 自动关闭文件）
    # 复用同一个 client 发多个请求，比每次 httpx.get() 新建连接快得多
    async with httpx.AsyncClient(timeout=5.0) as client:
        urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/1",
        ]
        start = time.perf_counter()
        try:
            responses = await asyncio.gather(*(client.get(u) for u in urls))
            codes = [r.status_code for r in responses]
            print(f"  3 个各需 1 秒的请求，并发耗时 {time.perf_counter() - start:.2f}s，状态码 {codes}")
        except httpx.HTTPError as err:
            # 网络不通时不影响学习，看懂写法即可
            print(f"  网络请求失败（不影响学习，看懂写法即可）：{type(err).__name__}")


# ==============================================================================
# 演示 10：AsyncOpenAI 真实并发调用大模型（可选，需要 .env）
# ==============================================================================


async def demo_async_openai():
    title("演示 10：AsyncOpenAI —— 并发问 3 个问题")

    try:
        from dotenv import load_dotenv
        from openai import AsyncOpenAI
    except ImportError:
        print("  缺少依赖：pip install openai python-dotenv")
        return

    # 从项目根目录的 .env 读取配置（与 pydantic使用/structured_output.py 相同的变量名）
    root_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    load_dotenv(root_env, override=True)
    api_key = os.getenv("api_key") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("base_url") or os.getenv("OPENAI_BASE_URL")
    model = os.getenv("mode") or os.getenv("OPENAI_MODEL_NAME")
    if not api_key:
        print("  未找到 api_key，跳过")
        return

    # AsyncOpenAI 与 OpenAI 的方法名完全一样，只是每次调用前要加 await
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60)

    async def ask(question: str) -> str:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"用一句话回答：{question}"}],
        )
        return resp.choices[0].message.content

    questions = ["什么是 RAG？", "什么是 MCP？", "什么是 LangGraph？"]
    start = time.perf_counter()
    answers = await asyncio.gather(*(ask(q) for q in questions), return_exceptions=True)
    print(f"  并发 3 个请求总耗时：{time.perf_counter() - start:.2f}s")
    for q, a in zip(questions, answers):
        print(f"  Q：{q}\n  A：{a}\n")

    await client.close()  # 关闭底层 httpx 连接池


# ==============================================================================
# 主入口
# ==============================================================================


async def main():
    await demo_lazy_coroutine()
    await demo_serial_vs_concurrent()
    await demo_gather_vs_taskgroup()
    await demo_as_completed_and_wait()
    await demo_timeout()
    await demo_semaphore()
    await demo_blocking_vs_to_thread()
    await demo_async_generator()
    await demo_httpx()
    if "--llm" in sys.argv:
        await demo_async_openai()
    else:
        print("\n💡 加上 --llm 参数可运行演示 10（真实调用大模型）")


if __name__ == "__main__":
    # asyncio.run：创建事件循环 → 运行 main() → 关闭循环
    # 整个程序只在入口处调用一次；FastAPI 中不要调用它（uvicorn 已经在运行循环）
    asyncio.run(main())
