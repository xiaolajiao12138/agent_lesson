# 门店设备报价 Agent

输入「预算 3000 元，想配一套门店收银设备」。模型通过工具调用提取预算，后端从模拟目录中选择有库存、接口兼容的主机、扫码枪和小票机，返回 2800 元报价草稿。

## 从仓库根目录启动

```powershell
python -m pip install -r quote-agent/requirements.txt
$env:QUOTE_API_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:QUOTE_DATABASE = 'quote-agent/quotes.db'
python -m uvicorn quote_agent:app_factory --factory --app-dir quote-agent --host 127.0.0.1 --port 8010
```

模型沿用根目录 config.py 的客户端、模型名称和地址。该模块会读取 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL_NAME 环境变量。按照已有课程配置启动即可。

访问 http://127.0.0.1:8010/docs，点击 **Authorize**，填入启动时设置的 `QUOTE_API_TOKEN` 原值。Swagger 会自动加上 `Bearer ` 前缀。展开 **POST /quotes** 并点击 **Try it out**。Idempotency-Key 填 `quote-demo-01`，请求体填 `{"request":"预算3000元，想配一套收银设备"}`。

缺少预算返回 needs_budget。补充预算后提交新请求并使用新幂等键。同一个键和同一个输入会返回首次保存的结果。改了输入却沿用同一个键会返回 409。

## 代码阅读顺序

源码的 Day 标记对应 [课程总表](../DAILY_CURRICULUM.md)。查看测试文件时，先找输入、模拟依赖和断言，再回到实现核对责任边界。

1. `model_budget(request)` 调用配置好的模型，通过 `Budget.model_json_schema()` 公开工具参数类型，通过 `model_validate_json()` 将模型返回的 JSON 转成校验过的对象。前者生成契约，后者验证数据。只接受一个已注册工具调用。
2. `make_quote(budget_cents)` 用 `itertools.product()` 枚举各品类的候选组合，再检查接口兼容性和总价。它适合小目录。商品量变大后可先按接口和库存缩小候选集，再用数据库查询或约束求解。
3. `create_app(database, token, extract_budget)` 将模型函数作为依赖传入。默认走真实模型，测试可以传本地函数。数据库唯一键和 `ON CONFLICT DO NOTHING` 保证同一请求只保存一份草稿。并发时模型本身仍可能被调用多次。
4. 请求日志记录关联 ID 和错误类型。可以用响应头 X-Request-ID 定位报价冲突或依赖故障。模型失败且当前没有已提交结果时返回 502，同一幂等键可以重试。数据库不可用时，就绪探针和报价请求返回 503。

```powershell
python -m pip install pytest httpx
Set-Location quote-agent
python -m pytest -q
```

本项目采用 SQLite、单服务凭证和模拟商品目录。企业部署环节可参考已有 phase08-enterprise-agent 的 PostgreSQL、Alembic、租户权限和 CI 示例。
