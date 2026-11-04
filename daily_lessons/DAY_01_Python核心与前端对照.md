# DAY 01 ~ DAY 03：Python 现代工程与前端概念对照速通

> **目标**：不按传统教材从“变量循环”慢慢学，而是站在 TypeScript / 前端工程视角，3 天内直接跨入现代 Python 3.11+、Pydantic v2 和 FastAPI 异步开发。

---

## 💡 为什么必须掌握 Python？（给前端的心理按摩）
在 Agent 领域，TypeScript 生态正在迅速崛起（如 Vercel AI SDK），但目前业界 80% 最新的研究、开源多 Agent 库（LangGraph、AutoGPT、CrewAI）和向量数据库底层仍然是 Python 优先。
好消息是：**现代 Python（带类型标注、异步 async/await、Pydantic 校验）与 TypeScript 的开发体感极其相似！**

---

## 1. 核心概念对比表

| 前端 / JS / TS | Python 现代工程 | 核心异同点与注意事项 |
| :--- | :--- | :--- |
| `npm` / `pnpm` | `uv` / `poetry` / `pip` | 推荐使用由 Rust 编写的极速包管理工具 `uv`（对标 `pnpm`）。 |
| `interface User { name: string }` | `class User(BaseModel): name: str` | 语法不同，但都是强类型约束。Python 的 Pydantic 还能在运行时做校验。 |
| `z.object({...}).parse(data)` | `Model(**data)` 或 `Model.model_validate(data)` | 失败均会抛出详细的校验异常（ZodError vs ValidationError）。 |
| `Promise.all([p1, p2])` | `await asyncio.gather(c1, c2)` | 都是并发调度多个异步协程任务。 |
| `Express` / `Next.js API` | `FastAPI` | FastAPI 原生基于类型注解，自动生成 Swagger 交互式文档。 |

---

## 2. 三大必须养成的 Python 现代习惯

### 规范一：永远写类型注解（Type Hints）
```python
# ❌ 旧时代的动态弱类型写法（不可取）
def process_data(item):
    return item["count"] * 2

# ✅ 现代类型标注写法（如同写 TypeScript）
from typing import Dict, Any

def process_data(item: Dict[str, Any]) -> int:
    return item.get("count", 0) * 2
```

### 规范二：使用 Pydantic 定义一切与大模型交互的结构
大模型本质上是一个不可靠的文本生成器。如果不做校验，大模型漏掉字段就会让下游系统直接崩溃。使用 Pydantic 可以保证：
1. **自动类型转换**：如果模型返回字符串 `"123"`，但字段定义为 `int`，Pydantic 会自动转为数字 `123`。
2. **Schema 自动导出**：可以直接通过 `MyModel.model_json_schema()` 导出给大模型的 Function Calling 使用。

### 规范三：异步（Asyncio）第一公民
大模型 API 交互是长 I/O 密集型操作，一次调用动辄 1~5 秒。**所有业务端点和工具函数一律写成 `async def`**，使用 `await`，禁止在主线程使用 `time.sleep()` 阻塞整个服务。

---

## 🛠️ 今日对应实战源码
请在终端中运行并阅读以下带有详尽注释的代码：
- 基础与异步：[`phase02-python-fastapi/day01_python_basics.py`](../phase02-python-fastapi/day01_python_basics.py)
- Pydantic v2 实战：[`phase02-python-fastapi/day02_pydantic_validation.py`](../phase02-python-fastapi/day02_pydantic_validation.py)
- FastAPI 异步网关：[`phase02-python-fastapi/day03_fastapi_server.py`](../phase02-python-fastapi/day03_fastapi_server.py)
