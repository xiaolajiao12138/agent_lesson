# DAY 50：Python 异步编程详解（asyncio 全家桶 + 异步调用大模型）

> **所属阶段**：phase07 后端工程化（P0 必修）  
> **配套代码**：[`phase07-backend-engineering/day50_async_python.py`](../phase07-backend-engineering/day50_async_python.py)  
> **学完能做什么**：同时调用多个大模型 / 工具而不卡死；给每个请求加超时；限制并发数防止被限流；写出 FastAPI 里不阻塞的异步接口和 SSE 流。

---

## 0. 为什么 Agent 开发必须学异步？

一个 Agent 一次请求里，大部分时间都在**等**：等大模型返回（2~30 秒）、等搜索接口、等数据库。

| 写法 | 3 个工具各要 2 秒 | 100 个用户同时访问 |
| :--- | :--- | :--- |
| 同步（`def` + `time.sleep`/`requests`） | 串行 6 秒 | 线程池被占满，后面的人排队 |
| 异步（`async def` + `await`） | 并发 2 秒 | 一个线程就能同时等成百上千个请求 |

---

## 1. 最核心的认知差异：Python 协程是“懒”的，JS Promise 是“勤快”的

```javascript
// JS：调用的一瞬间就开始执行了
const p = fetchData();   // 请求已经发出去了
```

```python
# Python：调用 async 函数只会得到一个“协程对象”，什么都不执行！
coro = fetch_data()      # 请求根本没有发出
result = await coro      # 直到 await（或交给事件循环调度）才真正开始执行
```

> [!IMPORTANT]
> 忘写 `await` 是新手最常见的 bug：你会拿到 `<coroutine object ...>` 而不是结果，并看到警告 `RuntimeWarning: coroutine '...' was never awaited`。

---

## 2. 基础关键字速查

| 语法 | 作用 | JS 对照 | 注意 |
| :--- | :--- | :--- | :--- |
| `async def f():` | 定义协程函数 | `async function f()` | 调用后返回协程对象，不会立即执行 |
| `await x` | 等待一个“可等待对象”完成并取结果 | `await x` | 只能写在 `async def` 里面（Jupyter 例外） |
| `async with` | 异步上下文管理器（进入/退出时可以 await） | 无直接对应，类似 `try/finally` 自动释放 | 用于 `httpx.AsyncClient`、数据库连接 |
| `async for` | 遍历异步迭代器（每拿一个元素都可能要等） | `for await (const x of stream)` | 用于流式输出 |
| `async def` + `yield` | 异步生成器 | `async function*` | FastAPI SSE 推流的标准写法 |

**“可等待对象（Awaitable）”有三种**：协程（coroutine）、任务（Task）、Future。日常只需要关心前两种。

---

## 3. 启动事件循环：`asyncio.run()` 及其同类

| 方法 | 作用 | 什么时候用 | 区别 |
| :--- | :--- | :--- | :--- |
| **`asyncio.run(main())`** | 创建事件循环 → 运行协程 → 关闭循环 | ✅ **脚本入口唯一推荐写法** | 一个程序通常只调用一次；不能在已运行的循环里调用 |
| `loop.run_until_complete(coro)` | 老式写法，手动拿 loop 再运行 | ❌ 旧代码里见到能看懂就行 | Python 3.7 之前的写法，要自己管理 loop |
| `asyncio.get_running_loop()` | 获取**当前正在运行**的循环 | 在 async 函数里需要 loop 对象时（如 `run_in_executor`） | 不在循环里调用会直接报错 |
| `asyncio.get_event_loop()` | 获取循环（没有就可能创建） | ❌ 新代码别用 | 3.10+ 已被逐步废弃，行为容易混乱 |
| Jupyter 里直接 `await main()` | Jupyter 自带运行中的循环 | Notebook 调试 | 在 Jupyter 里写 `asyncio.run()` 反而会报错 |

> [!NOTE]
> **FastAPI / uvicorn 已经替你运行了事件循环**，所以在接口函数里**永远不要**再调用 `asyncio.run()`，直接 `await` 就行。

---

## 4. 并发执行多个任务（本课重点）

### 4.1 五种方法对比总表

| 方法 | 作用 | JS 对照 | 返回值 | 一个失败了会怎样 | 推荐场景 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`asyncio.gather(*aws)`** | 并发运行，**按传入顺序**返回全部结果 | `Promise.all` | 结果列表（顺序与传入一致） | 第一个异常立即抛给你，**其他任务不会被取消**，继续在后台跑 | 最常用：并发调多个模型/工具 |
| `gather(..., return_exceptions=True)` | 同上，但把异常当成结果放进列表 | `Promise.allSettled` | 列表里混有结果和异常对象 | 不抛异常，需要自己 `isinstance(r, Exception)` 判断 | 多路召回，某一路失败不影响其他路 |
| **`asyncio.TaskGroup()`** (3.11+) | 结构化并发：在 `async with` 块里创建任务，退出块时等全部完成 | 无直接对应 | 通过 `task.result()` 取 | 一个失败 → **自动取消其他所有任务**，抛 `ExceptionGroup` | 新项目首选：要么全部成功，要么全部撤销 |
| `asyncio.create_task(coro)` | 立刻把协程丢给事件循环开始跑，返回 Task | 相当于 JS 不 await 直接调用 Promise | `Task` 对象，之后 `await task` 拿结果 | 异常在 `await task` 时才抛；如果从不 await，异常会被吞掉 | “先发出去，稍后再拿结果”；后台任务 |
| `asyncio.as_completed(aws)` | 谁先完成先返回谁 | 无直接对应（类似逐个 `Promise.race`） | 迭代器，按完成顺序产出 | 遍历到失败的那个时抛出 | 多个模型谁先回来先展示 |
| `asyncio.wait(tasks, return_when=...)` | 底层工具，返回 `(done, pending)` 两个集合 | `FIRST_COMPLETED` ≈ `Promise.race`；`FIRST_EXCEPTION`；`ALL_COMPLETED` | `(已完成集合, 未完成集合)` | 不抛异常，要自己检查 `task.exception()` | 需要精细控制：如拿到最快结果后取消其他 |

### 4.2 怎么选？

```text
需要全部结果？
 ├─ 是 → 某一个失败要不要撤销其他任务？
 │        ├─ 要（数据要一致）     → TaskGroup
 │        ├─ 不要，失败直接报错   → gather
 │        └─ 不要，失败也要拿其他 → gather(return_exceptions=True)
 └─ 否 → 只要最快的那个？
          ├─ 是 → wait(FIRST_COMPLETED) + 取消剩余
          └─ 想按完成顺序逐个处理 → as_completed
```

### 4.3 `await` 串行 vs `create_task` 并发 的经典陷阱

```python
# ❌ 看起来像并发，实际是串行（总耗时 = 2 + 2 = 4 秒）
a = await call_llm("A")   # 等 A 完成
b = await call_llm("B")   # 才开始 B

# ✅ 真正的并发（总耗时 ≈ 2 秒）
task_a = asyncio.create_task(call_llm("A"))  # 立刻开始
task_b = asyncio.create_task(call_llm("B"))  # 立刻开始
a = await task_a
b = await task_b
```

---

## 5. 超时控制

| 方法 | 作用 | 写法 | 超时后 | 区别 |
| :--- | :--- | :--- | :--- | :--- |
| **`asyncio.timeout(秒)`** (3.11+) | 给一整段代码块设超时 | `async with asyncio.timeout(5): ...` | 抛 `TimeoutError` | ✅ 新代码推荐；可以包住多行代码；可以中途改期限 `cm.reschedule()` |
| `asyncio.wait_for(aw, 秒)` | 给**单个**可等待对象设超时 | `await asyncio.wait_for(coro, 5)` | 抛 `TimeoutError`，并取消该任务 | 老写法，只能包一个协程 |
| `asyncio.timeout_at(时间点)` | 设到某个绝对时间点为止 | `async with asyncio.timeout_at(loop.time()+5)` | 同上 | 多个步骤共享同一个截止时间时用 |
| SDK 自带 `timeout=` 参数 | 网络层面的超时 | `AsyncOpenAI(timeout=30)`、`httpx.AsyncClient(timeout=10)` | 抛 SDK 自己的超时异常 | 只管网络请求；业务层整体超时仍需 `asyncio.timeout` |

> JS 对照：`AbortSignal.timeout(5000)` 或 `Promise.race([task, sleep(5000)])`。

---

## 6. 限制并发数：`Semaphore`（防止被大模型接口限流）

| 工具 | 作用 | JS 对照 | 典型场景 |
| :--- | :--- | :--- | :--- |
| **`asyncio.Semaphore(n)`** | 同一时刻最多 n 个任务进入 | `p-limit` 库 | 1000 个文档做 Embedding，但接口限制每次最多 5 个并发 |
| `asyncio.BoundedSemaphore(n)` | 同上，但多 release 一次会报错 | — | 想更严格地发现代码 bug |
| `asyncio.Lock()` | 同一时刻只允许 1 个（= `Semaphore(1)`） | 互斥锁 | 多个协程写同一个文件 / 同一个内存字典 |
| `asyncio.Queue(maxsize)` | 生产者-消费者队列 | — | 固定 N 个 worker 从队列里取任务处理 |

```python
sem = asyncio.Semaphore(5)

async def embed_one(text):
    async with sem:              # 进门：满 5 个就在这里排队
        return await call_embedding_api(text)
                                 # 出门：自动 release，让下一个进来
```

---

## 7. 在异步代码里调用“同步阻塞”的函数

**黄金规则**：`async def` 里面**绝对不能**出现会阻塞的同步调用（`time.sleep`、`requests.get`、同步数据库驱动、大文件 PDF 解析等），否则整个事件循环被冻住，所有用户一起卡。

| 方法 | 作用 | 区别 | 场景 |
| :--- | :--- | :--- | :--- |
| **`await asyncio.to_thread(func, *args)`** (3.9+) | 把同步函数丢到线程池执行，异步等它 | ✅ 最简洁，推荐 | 调用只有同步版本的库（如某些 PDF 解析库） |
| `loop.run_in_executor(None, func, *args)` | 同上，老写法 | 可以指定自定义线程池 / **进程池** | CPU 密集任务用 `ProcessPoolExecutor` |
| `asyncio.sleep(秒)` | 异步等待，让出控制权 | 对比 `time.sleep` 会冻住整个循环 | 模拟延迟、重试退避 |

| 阻塞写法 ❌ | 异步替代 ✅ |
| :--- | :--- |
| `time.sleep(1)` | `await asyncio.sleep(1)` |
| `requests.get(url)` | `await httpx.AsyncClient().get(url)` |
| `OpenAI().chat.completions.create()` | `await AsyncOpenAI().chat.completions.create()` |
| `open(f).read()`（大文件） | `await asyncio.to_thread(Path(f).read_text)` 或 `aiofiles` |
| `psycopg2` / `pymysql` | `asyncpg` / SQLAlchemy 异步引擎 |

---

## 8. HTTP 客户端对比：requests vs httpx vs aiohttp

| 库 | 同步 | 异步 | 特点 | 建议 |
| :--- | :---: | :---: | :--- | :--- |
| `requests` | ✅ | ❌ | 最老牌，API 最简单 | 只写同步小脚本时用 |
| **`httpx`** | ✅ `httpx.Client` | ✅ `httpx.AsyncClient` | API 和 requests 几乎一样；支持 HTTP/2；**OpenAI SDK 底层就是它** | ✅ Agent 项目首选 |
| `aiohttp` | ❌ | ✅ | 纯异步，性能略高，API 风格不同 | 极高并发爬虫场景 |

**`httpx` 的几个方法区别**：

| 写法 | 区别 |
| :--- | :--- |
| `httpx.get(url)` | 每次新建连接，用完即弃；适合偶尔调用一次 |
| `async with httpx.AsyncClient() as client: await client.get(url)` | **复用连接池**，多次请求快很多；✅ 推荐 |
| `client.get()` / `client.post(json=...)` / `client.stream("GET", url)` | `stream` 用于流式读取（逐块拿响应体，SSE 必用） |
| `resp.json()` / `resp.text` / `resp.raise_for_status()` | 解析 JSON / 取文本 / 状态码 ≥400 时抛异常（类似 `if (!res.ok) throw`） |

---

## 9. 异步调用大模型：OpenAI vs AsyncOpenAI

| 类 | 调用方式 | 适用 |
| :--- | :--- | :--- |
| `OpenAI` | `client.chat.completions.create(...)` | 脚本、同步 `def` 接口 |
| **`AsyncOpenAI`** | `await client.chat.completions.create(...)` | ✅ FastAPI `async def` 接口、并发调用 |

两者的方法名**完全一样**，异步版只是每个调用前加 `await`：

| 功能 | 同步 | 异步 |
| :--- | :--- | :--- |
| 普通调用 | `client.chat.completions.create(...)` | `await client.chat.completions.create(...)` |
| 结构化输出 | `client.chat.completions.parse(...)` | `await client.chat.completions.parse(...)` |
| 流式（原始） | `for chunk in client.chat.completions.create(stream=True)` | `async for chunk in await client.chat.completions.create(stream=True)` |
| 流式（高级） | `with client.chat.completions.stream(...) as s: for e in s` | `async with client.chat.completions.stream(...) as s: async for e in s` |

---

## 10. FastAPI 里 `def` 和 `async def` 接口的区别（面试高频）

| 接口写法 | FastAPI 怎么执行 | 里面可以写什么 |
| :--- | :--- | :--- |
| `def api():` | 自动扔进**线程池**执行（默认约 40 个线程） | 同步阻塞代码（`requests`、同步 `OpenAI`）没问题 |
| `async def api():` | 直接在**事件循环**里执行 | **只能**写异步代码；一旦写了 `time.sleep` 或同步 `OpenAI`，整个服务卡住 |

> [!CAUTION]
> 最危险的写法：`async def` 里调用同步的 `OpenAI().chat.completions.create()`。单人测试完全正常，一上线多人同时访问就会全部排队卡死。**要么全用同步 `def`，要么全用 `AsyncOpenAI`，不要混。**

---

## 11. 课后练习

1. 运行配套代码，观察每个演示的耗时数字，验证“串行 vs 并发”的差距。
2. 把 `demo_gather_vs_taskgroup` 里失败任务的延迟改成 0.1 秒，观察 `TaskGroup` 是否取消了其他任务。
3. 用 `Semaphore(2)` 改写 `demo_semaphore`，预测总耗时后再运行验证。
4. 进阶：改写你的 [`structured_output.py`](../pydantic使用/structured_output.py)，用 `AsyncOpenAI` + `async def` 接口重写 `/api/title`。
