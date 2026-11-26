"""企业实战第 1–7 课｜FastAPI 应用入口，衔接 Day 21–23 的依赖、日志和接口测试。

启动命令在 README.md 中，核心入口为 uvicorn support_agent.main:create_app --factory。
Uvicorn 调用 create_app() 装配应用，装饰器注册中间件和路由，收到请求后再执行对应函数。
请求顺序为中间件进入、参数与依赖准备、路由处理、响应生成、中间件返回。
本项目的业务接口返回 JSON 或 204 空响应，数据库依赖中的 yield 用于生命周期清理。
阅读本文件后，可沿 answer_question() 进入 knowledge.py，沿建单和审批函数进入 workflow.py。
"""

import logging
from collections.abc import Iterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .db import build_engine
from .knowledge import answer_question, remove_document, save_document
from .models import Document, Status, Ticket, TicketEvent
from .schemas import (
    DocumentInput,
    EventView,
    KnowledgeAnswer,
    QuestionInput,
    ReviewInput,
    TicketView,
)
from .security import Actor, current_actor, load_identities, require_reviewer
from .workflow import (
    TicketConflict,
    TicketNotFound,
    create_ticket,
    review_ticket,
    ticket_history,
    visible_ticket,
)

logger = logging.getLogger("uvicorn.error.support_agent")


# ==============================================================================
# 1. 核心依赖定义：带生命周期清理的数据库会话
# ==============================================================================


def get_session(request: Request) -> Iterator[Session]:
    """为依赖本函数的请求提供一个 SQLAlchemy Session，结束时由上下文管理器清理。

    request.app.state.sessions 是 sessionmaker 工厂，调用它创建 Session。
    Session 在需要执行 SQL 等操作时才申请实际数据库连接。
    yield session 将对象交给接口参数，依赖退出时离开 with 块并调用 Session.close()。
    close() 释放本次会话使用的资源，并结束未提交事务，连接按 Engine 配置归还连接池。
    with Session(...) 管理会话关闭，with session.begin() 进一步管理事务的提交与回滚。
    业务写操作的提交边界由各路由明确声明，单纯关闭 Session 并不表示业务已经提交。
    相关写法可以用 try/finally 调用 close()，本处用上下文管理器集中表达清理规则。
    """
    with request.app.state.sessions() as session:
        yield session


# ==============================================================================
# 2. Annotated 类型别名：现代 FastAPI 工业级标配
# ==============================================================================
# Annotated 的第一个参数是对象类型，后面附加 FastAPI 读取的依赖或参数校验信息。
# Database 等价于在每个参数上写 session: Session = Depends(get_session)。
# 类型别名复用同一条依赖声明，实际 Session 仍由 get_session() 在请求期间创建和交出。

Database = Annotated[Session, Depends(get_session)]
  = Annotated[Actor, Depends(current_actor)]
Reviewer = Annotated[Actor, Depends(require_reviewer)]
# Header 将参数 idempotency_key 对应到请求头 Idempotency-Key，长度和正则用于校验。
IdempotencyKey = Annotated[str, Header(min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9._-]+$")]
# Path 从 URL 中提取 source_id，Query 用于 ? 后的查询参数，Body 用于请求体。
SourceId = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")]


# ==============================================================================
# 3. 应用工厂函数 (Application Factory Pattern)
# ==============================================================================


def create_app(engine: Engine | None = None, identities: dict[str, Actor] | None = None) -> FastAPI:
    """创建并返回 FastAPI 应用，供 Uvicorn 和测试共同调用。

    engine 及 identities 可由测试显式传入，省略时从运行环境创建引擎并加载身份配置。
    本项目测试使用临时 SQLite 文件，或专用 PostgreSQL schema，具体见 tests/conftest.py。
    应用工厂通过参数装配不同依赖，直接定义全局 app 则是在模块加载时创建固定实例。
    函数中的 @app.get/post 等在工厂运行时注册，函数体在匹配的请求到达时执行。
    """
    actors = identities if identities is not None else load_identities()
    database = engine if engine is not None else build_engine()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """应用生命周期上下文，管理工厂自行创建的 Engine 的释放。

        @asynccontextmanager 将 async 生成器包装为异步上下文管理器。
        FastAPI 在启动阶段运行到 yield，应用运行期间保留上下文，正常关闭时执行 finally。
        这里的 Engine 已在 create_app() 中创建，因此此函数主要声明关闭阶段的清理行为。
        engine is None 表示引擎由应用创建，dispose() 释放该引擎池中的空闲连接资源。
        外部传入的引擎由调用方管理，测试可用同一数据库验证重启恢复。
        请求级 get_session() 也使用 yield，它的生命周期范围是单次请求。
        """
        try:
            yield
        finally:
            if engine is None:
                database.dispose()

    app = FastAPI(title="售后工单 Agent 实战", lifespan=lifespan)
    # app.state 保存该应用实例共享的资源。sessionmaker 是工厂，调用工厂才能得到 Session。
    app.state.sessions = sessionmaker(database)
    app.state.identities = actors

    # --------------------------------------------------------------------------
    # 全链路追踪中间件：计算请求耗时、自动注入 Request ID
    # --------------------------------------------------------------------------
    @app.middleware("http")
    async def record_request(request: Request, call_next):
        """为 HTTP 请求生成 ID、记录处理耗时，并把 ID 放到响应头。

        call_next 是 FastAPI 传入的下游处理函数，参数名可改，调用位置决定前后处理代码。
        await call_next(request) 之前准备计时信息，返回后取得响应对象和状态码。
        perf_counter() 适合计算时间差，time.time() 适合表示真实时间戳。
        这里的计时到取得下游响应对象为止，流式响应的后续完整发送时间需另行测量。
        异常时 logger.exception() 记录堆栈，客户端收到固定的 500 错误内容和请求 ID。
        logger 是标准库 logging 对象，使用 %s 等占位符传递参数，相关用法见 Day 22 的日志课程。
        """
        request_id = uuid4().hex
        started = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            # 捕获未知严重崩溃，保留异常调用栈，向前端返回安全友好的 500 提示并带上该 ID 方便排查
            logger.exception("request_id=%s unexpected_error", request_id)
            response = JSONResponse({"detail": "服务暂时异常"}, status_code=500)

        # scope 保存 ASGI 请求信息，路由模板可避免把具体工单 ID 逐个作为日志维度。
        # getattr 的第三个参数是属性缺失时的默认值，用于未匹配路由等情况。
        route = getattr(request.scope.get("route"), "path", "<unmatched>")
        logger.info(
            "request_id=%s method=%s route=%s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            route,
            status,
            (perf_counter() - started) * 1000,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    # --------------------------------------------------------------------------
    # 全局异常拦截器：业务异常统一映射为标准 HTTP 状态码
    # --------------------------------------------------------------------------
    @app.exception_handler(TicketNotFound)
    async def ticket_not_found(_request: Request, _error: TicketNotFound) -> JSONResponse:
        """将业务层 TicketNotFound 映射为 HTTP 404 JSON 响应。

        业务层抛出领域异常，路由装配层负责决定 HTTP 表达，方便业务函数被测试和其他入口复用。
        返回统一的不存在信息，同时覆盖资源不存在和当前身份不可见的情况。
        HTTPException 适合在 HTTP 依赖或路由中直接指定状态，本函数展示 exception_handler 集中映射。
        """
        return JSONResponse({"detail": "工单不存在"}, status_code=404)

    @app.exception_handler(TicketConflict)
    async def ticket_conflict(_request: Request, error: TicketConflict) -> JSONResponse:
        """将幂等参数冲突或审批状态冲突映射为 HTTP 409。

        str(error) 读取业务异常携带的提示，JSONResponse 同时明确响应正文和 HTTP 状态码。
        返回普通字典通常使用接口的默认成功状态，错误响应在这里显式指定状态。
        """
        return JSONResponse({"detail": str(error)}, status_code=409)

    # --------------------------------------------------------------------------
    # 健康检查探针（Kubernetes 生产部署标准）
    # --------------------------------------------------------------------------
    @app.get("/health/live")
    def live() -> dict[str, str]:
        """存活检查，确认应用能够处理 HTTP 请求。

        GET /health/live 返回进程内的简单结果，常用于判断是否需要重启应用。
        /health/ready 进一步访问数据库，用于判断此实例是否适合接收业务流量。
        """
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready(session: Database) -> dict[str, str]:
        """就绪检查，验证数据库连接以及三张核心表的查询结构。

        select(model) 构造查询，limit(0) 将返回行数设为零，execute() 真正发送 SQL。
        这仍会检查表和引用列是否可查询，同时减少读取业务记录的开销。
        SQLAlchemyError 覆盖连接或 SQL 执行相关故障，映射为 503 表示暂不可用。
        该检查覆盖基础查询能力，实际业务写入还由事务与业务测试验证。
        """
        try:
            for model in (Ticket, TicketEvent, Document):
                session.execute(select(model).limit(0))
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="数据库暂不可用或迁移未完成") from None
        return {"status": "ready"}

    # --------------------------------------------------------------------------
    # 智能体问答与工单业务接口
    # --------------------------------------------------------------------------
    @app.post("/agent/answer")
    def answer(payload: QuestionInput, actor: Identity, session: Database) -> KnowledgeAnswer:
        """POST /agent/answer 接收已校验问题，使用当前身份执行知识库检索。

        payload 是请求体，actor 与 session 由 Annotated 中的 Depends 提供。
        QuestionInput 会处理空白和长度，answer_question() 进一步限定租户与文档可见范围。
        返回 KnowledgeAnswer 后由 FastAPI 校验并序列化为 JSON。
        route='transfer' 是转人工建议，后续由客户端独立调用 POST /tickets 创建工单。
        """
        return answer_question(session, actor, payload.question)

    @app.post(
        "/tickets",
        status_code=201,
        responses={200: {"model": TicketView, "description": "幂等重放"}},
    )
    def open_ticket(
        payload: QuestionInput,
        idempotency_key: IdempotencyKey,
        actor: Identity,
        session: Database,
        response: Response,
    ) -> TicketView:
        """在一个事务中创建或复用工单，并返回可公开的工单视图。

        Idempotency-Key 请求头标识同一次创建操作，重试时复用，新操作使用新键。
        with session.begin() 正常退出时 flush 并提交，异常退出时回滚。
        create_ticket() 返回 (ticket, created)，created 决定本次 HTTP 状态。
        model_validate() 在事务内读取 ORM 属性并创建 Pydantic 响应对象。
        装饰器默认首次返回 201，复用已有工单时用 response.status_code 调整为 200。
        responses={200: ...} 补充 OpenAPI 描述，实际状态仍由运行中的 response 设置。
        """
        with session.begin():
            ticket, created = create_ticket(session, actor, payload.question, idempotency_key)
            # 在事务提交前完成 Pydantic 校验与数据装配，避免提交后 ORM 属性过期触发隐式二次查询
            view = TicketView.model_validate(ticket)
        if not created:
            response.status_code = 200
        return view

    @app.get("/tickets/{ticket_id}")
    def read_ticket(ticket_id: str, actor: Identity, session: Database) -> TicketView:
        """GET /tickets/{ticket_id} 读取当前身份可见的单个工单。

        路径中的 ticket_id 自动传给同名参数，Identity 和 Database 仍由依赖注入。
        visible_ticket() 在 SQL 查询条件中校验租户及所有者，随后转换为 TicketView。
        GET 承担读取，POST /tickets 承担创建，两者可以共享相同的响应模型。
        """
        return TicketView.model_validate(visible_ticket(session, actor, ticket_id))

    @app.post("/tickets/{ticket_id}/review")
    def review(
        ticket_id: str, payload: ReviewInput, actor: Reviewer, session: Database
    ) -> TicketView:
        """POST 审批操作，先检查审批员角色，再在事务中迁移工单状态。

        Reviewer 依赖会调用 require_reviewer()，ReviewInput 限定 approved/rejected。
        Status(payload.decision) 把合法字符串转为业务枚举，review_ticket() 执行条件更新及审计。
        数据库事务正常退出后，已装配的 TicketView 由 FastAPI 返回给客户端。
        """
        with session.begin():
            return TicketView.model_validate(
                review_ticket(session, actor, ticket_id, Status(payload.decision))
            )

    @app.get("/tickets/{ticket_id}/events")
    def events(ticket_id: str, actor: Reviewer, session: Database) -> list[EventView]:
        """读取单个工单的审计事件列表，要求当前用户具备审批员角色。

        ticket_history() 会先验证工单可见性，再按事件 ID 排序查询。
        列表推导式把每个 ORM 事件转换为 EventView，最后整体序列化为 JSON 数组。
        这里的 events 表示审计记录，接口一次性返回这些记录。
        """
        return [
            EventView.model_validate(event) for event in ticket_history(session, actor, ticket_id)
        ]

    @app.put("/knowledge/{source_id}", status_code=204)
    def put_document(
        source_id: SourceId, payload: DocumentInput, actor: Reviewer, session: Database
    ) -> Response:
        """PUT /knowledge/{source_id} 新增或替换指定租户中的知识文档。

        SourceId 校验路径编号，DocumentInput 校验请求体，Reviewer 校验操作者角色。
        tenant_id 从可信 actor 中取得，save_document() 使用联合主键执行 UPSERT。
        PUT 表达对指定资源的写入，本项目成功后返回 204 空响应，数据由数据库事务提交。
        相关的 PATCH 常用于部分更新，本项目采用提交完整文档的方式。
        """
        with session.begin():
            save_document(session, actor.tenant_id, source_id, payload)
        return Response(status_code=204)

    @app.delete("/knowledge/{source_id}", status_code=204)
    def delete_document(source_id: SourceId, actor: Reviewer, session: Database) -> Response:
        """DELETE 指定租户下的知识文档，成功返回 204 空响应。

        remove_document() 通过租户和文档编号限定删除条件，多次删除均可得到资源已移除的结果。
        权限与输入格式由依赖和类型别名校验，提交事务由这里的 session.begin() 管理。
        """
        with session.begin():
            remove_document(session, actor.tenant_id, source_id)
        return Response(status_code=204)

    # --factory 启动方式会取得这个返回值。工厂每次调用都会装配一个应用实例。
    return app
