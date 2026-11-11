# 企业实战第 6 课  自动化测试、故障注入与 Agent 评测

配套代码 [测试数据库和 fixture](../phase08-enterprise-agent/tests/conftest.py) · [接口验收用例](../phase08-enterprise-agent/tests/test_delivery.py) · [评测运行器](../phase08-enterprise-agent/evals/run.py) · [固定用例](../phase08-enterprise-agent/evals/cases.json)

## 1. 每类测试验证什么

| 要验证的事 | 方法 | 本课例子 |
| --- | --- | --- |
| 输入与业务规则是否执行 | 接口集成测试 | 422 校验、401/403/404、重试状态码。 |
| 并发与失败能否保持一致性 | 并发和故障注入测试 | 两个相反审批只有一个成功，审计写入失败会一起回滚。 |
| 业务效果是否达到预期 | 固定样例评测 | 有据回答、正确引用、跨租户隔离、资料不足时转人工。 |
| 部署后服务能否访问 | HTTP 冒烟测试 | 查就绪接口，用实际 URL 运行评测，完成一次审批闭环。 |

## 2. 测试代码的方法详解

| 方法 | 作用及参数 | 类似方法与何时使用 |
| --- | --- | --- |
| `@fixture` 和 `yield` | 在测试前准备数据库或客户端，测试后执行清理。函数级 fixture 给每条用例独立数据。 | `setup_method` / `teardown_method` 适合类式测试。`unittest.TestCase` 提供标准库的 `setUp` 和断言。 |
| `@pytest.mark.parametrize(...)` | 同一测试逻辑接收多组输入，每组分别报告结果。 | 单个测试里的循环适合验证一个不可分割流程，多个独立用例用参数化更容易定位。 |
| `monkeypatch.setenv(name, value)` | 临时替换环境变量，pytest 在测试结束时恢复。 | `unittest.mock.patch.dict(os.environ, ...)` 适合标准库测试。`app.dependency_overrides` 适合替换 FastAPI 的某个依赖。 |
| `with TestClient(app)` | 在进程内发请求，并执行 FastAPI 的启动和关闭生命周期。无需监听本地端口。 | `httpx.AsyncClient` 搭配 `ASGITransport` 适合异步测试，生命周期通常需要另行管理。`httpx.Client(base_url=...)` 访问真实运行的服务器。 |
| `Barrier(2).wait()` 和 `ThreadPoolExecutor.submit(...)` | 两个线程先等对方到达，再发请求，制造重叠执行的机会。Future 的 `.result(timeout=...)` 取结果或报告异常。 | `asyncio.gather()` 适合异步客户端。高并发压力和响应时间分布需要独立的压测场景。 |
| `event.listen()` / `event.remove()` | 在数据库执行 SQL 前注入教学异常，并在 `finally` 中清理监听器。 | Mock 适合单元测试的依赖隔离。用真实数据库测试事务时，在具体步骤注入异常能观测回滚后的状态。 |
| `response.raise_for_status()` | HTTP 响应不在 2xx 时抛出 `HTTPStatusError`。 | 直接断言 `status_code` 适合明确验证 409、422 等业务响应。 |

## 3. 运行测试与评测

项目目录中安装 `requirements-dev.txt` 后执行。测试为每个用例准备数据库，并跑真实迁移。设置 `TEST_DATABASE_URL` 时使用 PostgreSQL 的独立测试 schema，适合接专用测试库。

```powershell
python -m pytest -q
python -m pytest -q -k concurrent
# 另开终端，在服务启动且已导入教学文档后运行
python -m evals.run --base-url http://127.0.0.1:8000
```

`load_cases()` 校验评测 JSON。`run_cases()` 用真实 API 契约比较路由、来源和原文；执行器返回失败清单，CLI 有失败时退出码为 1。八条案例适合当回归起点。接入生成模型后，评测可改成逐项判定引用、事实和任务结果，并抽样人工复核。 [OpenAI 评测设计指南](https://developers.openai.com/api/docs/guides/evaluation-best-practices)

## 4. 动手验收

先记录 8 条样例的结果。更新关键词或检索策略后重新运行。用新问题补充测试时，写明身份、期望路由、来源和通过条件，保留部分真实场景作为独立验证集。练习再增加一个失败场景，确认测试先失败，修复后恢复通过。
