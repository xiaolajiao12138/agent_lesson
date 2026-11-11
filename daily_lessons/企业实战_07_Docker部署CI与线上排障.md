# 企业实战第 7 课  Docker Compose、CI、回滚与线上排障

配套代码 [Dockerfile](../phase08-enterprise-agent/Dockerfile) · [Compose](../phase08-enterprise-agent/compose.yaml) · [GitHub Actions](../.github/workflows/enterprise-agent.yml) · [健康检查和日志](../phase08-enterprise-agent/support_agent/main.py)

## 1. 先跑通一次可重复的发布

按 [项目启动说明](../phase08-enterprise-agent/README.md) 启动 PostgreSQL 与 API。Compose 启动顺序为数据库健康、迁移成功、API 启动。API 监听宿主机回环地址，适合本地练习。数据库数据保存在命名卷里，服务容器替换后仍能连接同一份数据。 [Docker Compose 启动顺序](https://docs.docker.com/compose/how-tos/startup-order/)

| 配置或命令 | 作用 | 类似方法与场景 |
| --- | --- | --- |
| `COPY requirements.txt .` + `RUN pip install ...` | 将依赖安装与业务代码复制拆成两层，改业务代码时可以复用依赖层。 | `uv sync --locked` 适合采用 uv 并维护完整锁文件的项目。本例固定直接依赖版本。 |
| `USER 10001:10001` | 以非 root 的用户和组运行服务。 | 开发镜像可使用具名用户。容器在受管平台上还可以配置只读文件系统和运行权限。 |
| `depends_on: condition: service_healthy` | 依赖服务通过健康检查后再启动。 | `service_started` 只等待启动。`service_completed_successfully` 等待一次性迁移任务成功退出。 |
| `docker compose up -d --build` | 构建应用镜像并后台启动依赖服务。 | `docker compose run --rm api ...` 运行一次性命令，例如导入数据。`docker compose exec api ...` 在运行中的容器里执行命令。 |
| `docker compose down` | 停止并移除项目容器和网络，命名卷默认保留。 | `stop` 仅停止容器。`down -v` 同时删除课程数据库卷，适合明确要清空课程数据时。 |

## 2. 区分健康检查与请求追踪

| 方法 | 做什么 | 使用场景 |
| --- | --- | --- |
| `GET /health/live` | 返回进程能处理 HTTP 请求。 | 验证服务进程是否存活。 |
| `GET /health/ready` | 对业务表执行轻量查询，访问失败返回 503。 | 部署后决定是否接收业务请求，诊断迁移或数据库连接问题。 |
| `uuid4().hex` | 生成随机请求 ID，写入响应头及日志。 | 多服务链路使用 OpenTelemetry 的 Trace ID 和 Span ID 传递因果关系。 |
| `perf_counter()` | 返回用于测量经过时长的高精度计时值。计算前后差值得到响应耗时。 | `datetime.now()` 记录墙上时钟时间，适合事件发生时间。 |
| `logger.info(..., args)` | 由日志模块按模板填入参数。这里记录路由、状态和耗时。 | JSON 结构化日志适合按字段过滤。Day 43 的模型 Trace 可以进一步记录检索、工具和 Token 成本。 |

排障顺序从症状出发。请求不通先查端口与 `live`。请求可达但 `ready` 返回 503 时查数据库与迁移日志。业务返回 409 时看工单终态及审计。返回 500 时取 `X-Request-ID` 去服务端找相关日志，查看异常位置，再选择对应修复。

## 3. CI 和发布回滚各自验证什么

GitHub Actions 在课程目录的变更触发时安装依赖，对 SQLite 与 PostgreSQL 分别迁移、检查结构差异并执行测试。PostgreSQL 用服务容器提供。评测也会通过一个集成用例运行，改坏引用或路由会使任务失败。 [GitHub Actions PostgreSQL 服务容器文档](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)

课程的部署命令由开发者手动运行。真实发布可保存每次构建的镜像版本，在测试环境验收后发布到目标环境。回滚应用时先确认旧镜像兼容当前表结构，再切回上一个已验证版本。数据库变更优先拆成兼容旧应用和新应用的步骤，便于回滚代码。需要回退数据时应有经过演练的备份恢复方案。

## 4. 动手验收

1. 启动服务、查 `/health/ready`、导入文档、运行评测。
2. 创建一张待审批工单，重启 API 容器，用同一个 ID 完成审批。
3. 停掉课程数据库，确认 API 的 `/health/ready` 返回 503。重新启动数据库并验证恢复。
4. 用一次业务请求的 `X-Request-ID` 找到日志。记录部署步骤和验证结果，交给另一个人按说明复现。
