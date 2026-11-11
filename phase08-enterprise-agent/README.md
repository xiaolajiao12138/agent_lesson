# 售后工单 Agent 企业工程实战

企业交付实战七课共用一个可运行的 FastAPI 项目。你会完成知识库问答、转人工工单、审批、查询结果，再验证重复请求、越权、重启恢复和部署。

## 课程与代码

| 课时 | 实战内容 | 代码入口 |
| --- | --- | --- |
| [第 1 课 需求拆解与状态机](../daily_lessons/企业实战_01_需求拆解与工单状态机.md) | 写验收条件和 API 契约 | [models.py](support_agent/models.py)、[schemas.py](support_agent/schemas.py) |
| [第 2 课 SQLAlchemy 与 Alembic](../daily_lessons/企业实战_02_SQLAlchemy事务与Alembic迁移.md) | 表结构、请求级 Session、事务和迁移 | [db.py](support_agent/db.py)、[迁移文件](migrations/versions/0001_initial.py) |
| [第 3 课 状态恢复与幂等](../daily_lessons/企业实战_03_状态恢复幂等与并发.md) | 重启后审批、重复提交、并发审批、事务回滚 | [workflow.py](support_agent/workflow.py) |
| [第 4 课 鉴权和审计](../daily_lessons/企业实战_04_鉴权数据隔离与审计.md) | 身份验证、角色授权、租户与资源隔离 | [security.py](support_agent/security.py)、[main.py](support_agent/main.py) |
| [第 5 课 知识库生命周期](../daily_lessons/企业实战_05_知识库导入更新与检索.md) | 导入、更新、下架、带出处回答、转人工 | [knowledge.py](support_agent/knowledge.py)、[seed.py](support_agent/seed.py) |
| [第 6 课 测试和评测](../daily_lessons/企业实战_06_自动化测试与Agent评测.md) | 回归评测、故障注入、并发测试 | [测试](tests/test_delivery.py)、[评测运行器](evals/run.py) |
| [第 7 课 部署和排障](../daily_lessons/企业实战_07_Docker部署CI与线上排障.md) | Compose、CI、健康检查与日志 | [compose.yaml](compose.yaml)、[CI](../.github/workflows/enterprise-agent.yml) |

课程服务使用关键词检索和原文摘录，方便离线复现和评分。你可以在掌握业务闭环后接入 Day 9–11 的向量检索或 Day 24 的 LangGraph 审批编排。现有审批的执行结果是工单状态和审计事件。

## 1. 用 SQLite 本地启动

以下命令适用 Windows PowerShell 和 Python 3.12。从学习仓库根目录进入项目。默认数据库 `support_agent.db` 会留在项目目录，重启服务时继续使用。

```powershell
Set-Location phase08-enterprise-agent
python -m venv .venv
$coursePython = '.\.venv\Scripts\python.exe'
& $coursePython -m pip install -r requirements-dev.txt
$env:DATABASE_URL = 'sqlite:///./support_agent.db'
$env:AGENT_IDENTITIES_JSON = Get-Content -LiteralPath demo-identities.json -Raw -Encoding utf8
& $coursePython -m alembic upgrade head
& $coursePython -m support_agent.seed
& $coursePython -m uvicorn support_agent.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

打开 [Swagger 接口文档](http://127.0.0.1:8000/docs)。点击 **Authorize**，输入 [教学身份文件](demo-identities.json) 中的 token。课堂使用公开示例凭证和本地回环地址。

## 2. 走一遍完整业务流程

另开一个 PowerShell，进入项目目录后执行。第一段验证引用与转人工，第二段建单、审批并重试，第三段查看审计和最终状态。

```powershell
$api = 'http://127.0.0.1:8000'
$contentType = 'application/json; charset=utf-8'
$customer = @{ Authorization = 'Bearer training-blue-customer-000001' }
$reviewer = @{ Authorization = 'Bearer training-blue-reviewer-000001' }

Invoke-RestMethod "$api/health/ready"
Invoke-RestMethod "$api/agent/answer" -Method Post -Headers $customer -ContentType $contentType -Body (@{ question = '怎么退货？' } | ConvertTo-Json)
$question = @{ question = '怎么预约上门安装？' } | ConvertTo-Json
Invoke-RestMethod "$api/agent/answer" -Method Post -Headers $customer -ContentType $contentType -Body $question

# 同一次建单操作重试时保留同一把键，每次新操作生成新的键。
$createHeaders = $customer.Clone()
$createHeaders['Idempotency-Key'] = [guid]::NewGuid().ToString()
$ticket = Invoke-RestMethod "$api/tickets" -Method Post -Headers $createHeaders -ContentType $contentType -Body $question
$replay = Invoke-RestMethod "$api/tickets" -Method Post -Headers $createHeaders -ContentType $contentType -Body $question
if ($replay.id -ne $ticket.id) { throw '幂等重放返回了不同的工单' }
$reviewUrl = "$api/tickets/$($ticket.id)/review"
$decision = @{ decision = 'approved' } | ConvertTo-Json
Invoke-RestMethod $reviewUrl -Method Post -Headers $reviewer -ContentType $contentType -Body $decision
Invoke-RestMethod $reviewUrl -Method Post -Headers $reviewer -ContentType $contentType -Body $decision

Invoke-RestMethod "$api/tickets/$($ticket.id)/events" -Headers $reviewer
Invoke-RestMethod "$api/tickets/$($ticket.id)" -Headers $customer
```

预期退货问题返回 `answer` 和 `returns` 引用，安装问题返回 `transfer`。最终工单为 `approved`，审计只有 `created` 和 `approved` 两条。

## 3. 跑测试与效果评测

```powershell
$coursePython = '.\.venv\Scripts\python.exe'
& $coursePython -m pytest -q
# 评测脚本访问已启动且导入教学数据的 API
& $coursePython -m evals.run --base-url http://127.0.0.1:8000
```

集成测试自动运行迁移并给每条用例准备独立数据库。要在专用 PostgreSQL 测试库跑同一组用例，把 `TEST_DATABASE_URL` 设置为 `postgresql+psycopg://用户:密码@地址:5432/库名`，测试用户需要创建 schema 的权限。测试为每条用例创建并清理自己命名的 schema。

## 4. 用 Compose 启动 PostgreSQL 版

安装带 Compose 的 Docker 环境。先停止占用宿主机 8000 端口的本地 Uvicorn，再从本项目目录运行。

```powershell
if (-not (Test-Path -LiteralPath '.env')) {
    $dbPassword = python -c "import secrets; print(secrets.token_hex(24))"
    Set-Content -LiteralPath '.env' -Value "POSTGRES_PASSWORD=$dbPassword" -Encoding ascii
}
$env:AGENT_IDENTITIES_JSON = Get-Content -LiteralPath demo-identities.json -Raw -Encoding utf8
docker compose up -d --build
docker compose ps -a
docker compose logs migrate
docker compose run --rm api python -m support_agent.seed
Invoke-RestMethod 'http://127.0.0.1:8000/health/ready'
```

`migrate` 正常退出、API 就绪后可重复第 2 节操作。上面的命令首次启动时把随机数据库密码保存在当前项目的 `.env` 里，重启同一数据库卷时继续使用它。学习结束可用 `docker compose down` 停止课程服务并保留数据。
