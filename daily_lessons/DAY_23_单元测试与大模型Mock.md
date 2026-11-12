# DAY 23：智能体单元测试与大模型 Mock（pytest + pytest-asyncio + AsyncMock）

> **所属阶段**：phase07 后端工程化（P0 必修）  
> **配套代码**：[`phase07-backend-engineering/day53_pytest_mock_llm.py`](../phase07-backend-engineering/day53_pytest_mock_llm.py)  
> **学完能做什么**：彻底解决“测试大模型又慢又费 Token”的痛点；掌握 `pytest` 现代测试体系，掌握用 `AsyncMock` 模拟大模型与搜索工具返回，做到 0 秒响应、0 Token 消耗，且能精准测试大模型报错时的兜底降级逻辑。

---

## 1. 为什么做 Agent 项目必须掌握 Mock？

在传统 Web 测试中，我们可能会偶尔连真实测试库；但在 **AI Agent** 开发中，**绝对不能在日常跑自动化测试时真实调用大模型**：

1. **钱包承受不住（Token 爆炸）**：
   * 假设你有 30 个自动化测试用例，每次保存代码（或 Git 提交 push 时跑 CI/CD）都跑一次；
   * 一天跑 20 次 = 每天调用大模型 600 次！一个月下来测试费能花掉上千元。
2. **耗时极长，反馈周期慢**：
   * 真实调用大模型一次通常需要 2~10 秒；30 个用例全部真实调用需要跑 **2~5 分钟**！
   * 而使用 Mock 伪造结果，30 个测试在 **0.2 秒** 内全部跑完，开发体验天差地别。
3. **输出不确定性（Flaky Test 噩梦）**：
   * 大模型是有随机性（Temperature）的，今天返回 `"YES"`，明天可能偶发返回 `"Sure, yes"`；
   * 如果不 Mock，你的单元测试随时会因为大模型随机措辞变化而偶发失败。
4. **无法测试极端异常（大模型宕机、超时、限流）**：
   * 你怎么验证“当 OpenAI 报 500 宕机时，你的 Agent 会不会自动降级切到本地 DeepSeek”？
   * 难道去祈祷 OpenAI 真的宕机？只能通过 **Mock 强制抛出异常** 来验证！

---

## 2. 测试框架对比：`unittest` vs `pytest`

| 对比维度 | Python 标准库 `unittest` | 现代标准 `pytest` 🌟 |
| :--- | :--- | :--- |
| **组织形式** | 必须写 Class 继承 `unittest.TestCase`，样板代码多 | **极简纯函数**：以 `test_` 开头的普通函数即可 |
| **断言语法** | 记忆一堆长方法：`self.assertEqual(a, b)`、`self.assertIn(x, y)` | **原生 Python `assert`**：`assert a == b`，失败时自动打印变量表达式的值 |
| **异步测试支持** | 3.8+ 引入 `IsolatedAsyncioTestCase`，写法重 | 搭配 `pytest-asyncio`，直接写 **`async def test_xxx():`** 即可！ |
| **数据驱动（参数化）** | 需借助外部库 `ddt` 或手动写循环 | **`@pytest.mark.parametrize`**：一行装饰器同时跑几十组测试数据 |
| **共享夹具（Fixtures）** | 只能用 `setUp` / `tearDown`，复用性差 | **`@pytest.fixture`**：类似 FastAPI 的 `Depends` 依赖注入，支持作用域与自动清理 |
| **生态插件** | 几乎没有插件生态 | `pytest-asyncio`、`pytest-cov`（代码覆盖率）、`pytest-mock` |

---

## 3. Mock 核心方法对比：`MagicMock` vs `AsyncMock` vs `dependency_overrides`

在前端 Jest / Vitest 中，我们常用 `vi.fn()` 或 `jest.spyOn()`；在 Python 中，标准库 `unittest.mock` 提供了完全对应的强大武器。

### 3.1 三大 Mock 方式全方位对比表

| Mock 工具 | 针对目标 | 区别与注意事项 | 典型场景 |
| :--- | :--- | :--- | :--- |
| **`MagicMock`** | 普通同步函数 / 对象 / 类 | 模拟普通属性和方法（如 `.strip()`, `.json()`） | 模拟普通的工具函数（如本地计算器、文件读取） |
| **`AsyncMock`** 🌟 | **`async def` 协程函数** | **返回值自动被包装为可等待对象 (Awaitable)**！如果用普通 `MagicMock` 去 mock 异步函数，运行时会报 `TypeError: object MagicMock can't be used in 'await' expression`！ | **Mock `AsyncOpenAI.chat.completions.create`**、Mock 异步网络请求 `httpx.get` |
| **`app.dependency_overrides`** 🌟 | FastAPI 接口中的 `Depends` | **非侵入式**：不需要改动任何业务代码或打补丁，直接在 FastAPI 路由级别替换鉴权或数据库 | 测试不需要登录、使用假数据库跑接口测试 |
| **`monkeypatch`** | 模块属性、系统环境变量 | pytest 内置夹具，测试结束后自动恢复原本环境 | 临时修改 `os.environ` 测试配置开关 |

---

## 4. 真实大模型 Mock 的标准写法

OpenAI SDK 返回的对象层级很深：`completion.choices[0].message.content`。我们要怎么 Mock 出一个结构一模一样的伪造对象？

### 4.1 手动拼装法（结构清晰）
```python
from unittest.mock import AsyncMock, MagicMock

# 1. 伪造 message
mock_message = MagicMock()
mock_message.content = "这是伪造的大模型回答"
mock_message.parsed = {"user_name": "小陈", "skills": ["React", "Python"]}

# 2. 伪造 choice
mock_choice = MagicMock()
mock_choice.message = mock_message

# 3. 伪造 completion 顶层对象
mock_completion = MagicMock()
mock_completion.choices = [mock_choice]
mock_completion.usage.total_tokens = 42

# 4. 把 AsyncOpenAI 的 create 方法替换成一个 AsyncMock
mock_client = MagicMock()
mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

# 验证调用：
# resp = await mock_client.chat.completions.create(...)
# resp.choices[0].message.content -> "这是伪造的大模型回答"（瞬间返回，0 Token 消耗！）
```

---

## 5. 模拟大模型故障：测试“重试与容错降级”

最能体现高级 Agent 工程师功底的，是**针对错误场景的测试**：
```python
# 模拟大模型第一次调用超时，第二次调用成功
mock_client.chat.completions.create = AsyncMock(
    side_effect=[
        TimeoutError("网关连接超时"),          # 第 1 次调用：抛异常
        mock_completion                     # 第 2 次调用：成功返回
    ]
)
```
通过 `side_effect` 参数，可以按顺序指定每次调用是成功还是抛出指定异常，轻松测试你的 Agent 在大模型网络波动时的重试韧性！
