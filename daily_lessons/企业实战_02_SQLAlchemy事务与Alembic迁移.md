# 企业实战第 2 课  FastAPI 后端、SQLAlchemy 事务与 Alembic 迁移

配套代码 [数据库连接](../phase08-enterprise-agent/support_agent/db.py) · [模型定义](../phase08-enterprise-agent/support_agent/models.py) · [首个数据库迁移](../phase08-enterprise-agent/migrations/versions/0001_initial.py) · [路由与 Session](../phase08-enterprise-agent/support_agent/main.py)

## 1. 先识别三个生命周期

| 对象 | 在项目里的寿命 | 负责什么 |
| --- | --- | --- |
| `Engine` | 一个应用进程内复用 | 管理数据库连接和连接池，持有数据库方言。 |
| `Session` | 每次请求独立创建 | 执行 SQL、管理 ORM 对象、协调事务。 |
| 事务 | 一次业务写入期间 | 把工单状态与审计事件作为一个提交单元。 |

`build_engine()` 支持 SQLite 文件和 PostgreSQL + Psycopg。课堂先用 SQLite 跑通，然后用 PostgreSQL 验证生产中使用的数据库方言和并发语义。API 的数据库操作使用同步 SQLAlchemy 和普通 `def` 路由，FastAPI 将同步路由放入线程池。迁移到异步方案时，需要一起换成异步驱动、`AsyncSession` 和 `async def` 路由。

## 2. 逐个读常用方法

| 方法 | 参数、返回和副作用 | 类似方法与场景 |
| --- | --- | --- |
| `create_engine(url, pool_pre_ping=True)` | 接收连接 URL，返回可复用的 Engine。PostgreSQL 连接从池里借出前会做存活检查。首次连库发生在实际需要连接时。 | `create_async_engine()` 供异步驱动使用。`engine.connect()` 借出一条连接。`engine.begin()` 同时建立事务上下文。 |
| `sessionmaker(engine)` | 返回 Session 工厂，调用 `factory()` 得到一个独立 Session。 | `Session(engine)` 适合一次性脚本。`factory.begin()` 适合脚本里一次创建、提交并关闭 Session。 |
| `with session.begin():` | 正常退出时 flush 并提交，异常退出时回滚，异常继续传给上层。调用时 Session 里不应已有开启的事务。 | 显式 `commit()/rollback()` 适合由更上层管理事务的逻辑。`begin_nested()` 建立保存点，适合事务内局部回退。 |
| `session.add(obj)` | 将对象加入 Session。等待 flush 后发出 INSERT。 | `session.execute(insert(...))` 执行已构造的 SQL 表达式，便于使用方言的 `ON CONFLICT`。 |
| `session.flush()` | 将待写 SQL 发送到数据库，可获得生成的 ID，也会触发约束检查。事务此时仍可回滚。 | `session.commit()` 提交整个事务。`session.refresh(obj)` 重新从库读取对象属性。 |
| `select(Ticket).where(...)` | 构造查询。多个条件以 AND 连接，执行后才从数据库读数据。 | `session.get(Ticket, id)` 适合可信范围内按主键取对象。`where()` 可以同时表达租户、所有者和状态条件。 |
| `session.scalars(query).one_or_none()` | `scalars()` 取每行的第一列，选 ORM 模型时得到模型对象。随后要求至多一项，多项会报错。 | `.one()` 要求刚好一项。`.first()` 取第一项或空值，查询较大时显式加 `.limit(1)`。`.all()` 读取全部结果。 |

`get_session()` 使用 `yield` 将 Session 交给 FastAPI 依赖注入。资源清理在退出上下文时发生。写路由在返回成功响应前完成事务提交，数据库错误可以反馈给客户端。

## 3. 在数据库里表达业务约束

- `UniqueConstraint` 把幂等键限定在租户和用户组合内。跨用户使用同一键是两个不同请求。
- `ForeignKey("tickets.id")` 保证审计事件指向真实工单。代码为 SQLite 的每条新连接打开外键检查。
- `CheckConstraint` 限制可存储状态。状态迁移规则在条件 UPDATE 中执行。
- `Index("ix_ticket_events_ticket_id", "ticket_id", "id")` 支持按工单过滤并按事件 ID 排序。可以对比有无该索引时的 `EXPLAIN` 输出。

## 4. 管理表结构变更

在项目目录运行这些命令，使用 [启动说明](../phase08-enterprise-agent/README.md) 中的虚拟环境。

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

| 命令 | 做什么 | 何时使用 |
| --- | --- | --- |
| `upgrade head` | 把已存在的数据库推进到最新 revision，并写入迁移版本。 | 本地初始化和部署前迁移。 |
| `current` / `history` | 分别显示当前数据库版本、仓库中已有的迁移历史。 | 诊断版本落后和迁移顺序。 |
| `check` | 检查模型与数据库之间是否存在 Alembic 可检测的待生成操作。 | 在 CI 检查模型修改是否配了迁移。约束及数据变更还需人工检查。 |
| `revision --autogenerate -m "add priority"` | 通过模型与数据库的差异生成候选迁移。 | 修改模型后生成初稿，审阅变更、默认值和 downgrade 再执行。 |
| `upgrade head --sql` | 输出将执行的 SQL，用于评审。 | 上线前或数据库由专人管理时。 |

`Base.metadata.create_all()` 适合一次性实验建表。现有库的演进使用版本化迁移，方便团队复现顺序。初始迁移的 `downgrade()` 会删表，先在可丢弃的课程库做回退练习。

## 5. 动手验收

查看 `alembic current` 的输出，创建工单后再运行 `upgrade head`，确认已有记录可查。然后改一次模型，例如给工单加一个可空优先级字段，在自己的练习分支生成并审阅迁移。想清楚存量工单的默认值和回退行为后再运行。

[SQLAlchemy Session 文档](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) · [Alembic 教程](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
