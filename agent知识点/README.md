# Agent 课程知识点

课号以当前 [每日课程表](../DAILY_CURRICULUM.md) 为准，适合按「学知识点 → 默写小功能 → 用测试验收」复习。

| 课时 | 知识点 | 动手检查 |
| --- | --- | --- |
| Python 先修 | 变量、类型、列表与字典、控制流与推导式、函数和动态传参、类与 self、异常和文件、模块与虚拟环境 | 从 JSON 读取库存，封装查询函数并处理文件错误 |
| Day 1 | Python 现代工程、类型注解及 JS/TS 对照 | 给库存函数写参数与返回类型 |
| Day 2 | Pydantic v2、字段约束、自定义校验、JSON Schema | 拒绝负数库存和缺字段的数据 |
| Day 3 | FastAPI 路由、请求体和响应模型、Swagger | 在 /docs 发请求并验证 422 |
| Day 5 | LLM 消息、Token、上下文窗口、流式输出 | 区分完整响应和增量事件 |
| Day 7 | Prompt、结构化输出、解析与校验 | 将模型结果校验为 Pydantic 对象 |
| Day 9 | RAG 数据预处理、切分、嵌入、向量召回 | 同一问题验证不同分块策略 |
| Day 11 | 检索优化、Rerank、引用溯源 | 检查回答引用能否定位到原文 |
| Day 12 | 把 RAG 封装为可调用工具 | 检查直接回答、调用检索和无资料三条分支 |
| Day 13 | Tool Calling、手写 ReAct 循环、工具结果回填 | 处理未知工具、非法参数和循环上限 |
| Day 14 | LangGraph State、Node、Edge、条件路由 | 根据状态路由到处理或人工节点 |
| Day 15 | 人工审批、检查点、暂停与恢复 | 暂停后从同一状态继续 |
| Day 16 | Supervisor、多 Agent 分工与终止 | 验证任务分发及明确结束条件 |
| Day 17 | MCP Server、工具 Schema、客户端发现与调用 | 注册工具并从客户端调用 |
| Day 18 | Langfuse、Trace/Span、时延与 Token | 从一条请求定位失败步骤 |
| Day 19 | FastAPI SSE、前端流式消息、Generative UI | 把增量文本和审批事件渲染为不同组件 |
| Day 20 | asyncio、任务、并发、超时、取消、限流 | 对比串行与并发并验证超时行为 |
| Day 21 | FastAPI lifespan、Depends、路由拆分、全局异常、上传与后台任务 | 区分请求级资源和进程级资源 |
| Day 22 | 环境配置、日志级别、关联 ID 和日志轮转 | 用请求 ID 找到对应日志 |
| Day 23 | pytest、fixture、Mock 模型与异常分支 | 模型超时时测试稳定通过 |
| Day 24 | 业务需求、接口契约、工单状态机与验收 | 明确每种状态允许的操作 |
| Day 25 | SQLAlchemy Engine/Session、事务、约束、Alembic | 空库迁移并验证回滚 |
| Day 26 | 状态持久化、幂等键、条件更新、并发与故障恢复 | 重试只留一条记录 |
| Day 27 | 认证、角色授权、数据隔离和审计 | 覆盖同租户、跨租户和无角色场景 |
| Day 28 | 知识库导入、更新、下架、检索基线 | 下架后检索结果立即变化 |
| Day 29 | 软件测试、Agent 评测集、故障注入和回归 | 同时核对业务结果与证据 |
| Day 30 | Docker Compose、CI、健康检查、发布回滚与排障 | 根据健康检查和请求 ID 定位部署问题 |

## 阅读与实战入口

- [Python 零基础手册](../daily_lessons/PYTHON_00_前端零基础转Python精讲手册.md)和 [完整课表](../DAILY_CURRICULUM.md)包含原始讲义、练习代码和阶段索引。
- [全链路选型指南](../AI_AGENT全链路技术架构与选型指南.md)覆盖前端通信、上下文和记忆、网关、模型选型、工具执行与可观测性。
- [门店设备报价 Agent](../quote-agent/README.md)用 Pydantic 校验模型的工具调用，用代码计算报价，练习 FastAPI、鉴权、持久化、幂等和测试。
- [售后工单实战](../phase08-enterprise-agent/README.md)可继续练习迁移、工单审批、知识库生命周期与部署。

复习时每次只记三件事：方法接收什么、返回什么、失败时如何处理。比如 `json.loads()` 负责解析、`Budget.model_validate_json()` 同时解析并校验字段。关掉示例后用一份新输入重写，再用测试检查正常和失败分支。
