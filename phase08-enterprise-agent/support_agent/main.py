"""
================================================================================
企业实战：FastAPI 应用装配、全链路中间件与依赖注入契约中心
================================================================================
本模块是企业级售后智能体服务的总装配入口（API Gateway / Controller 层）。
涵盖核心机制与类似方法深度对比：
    1. 【Annotated 依赖注入最佳实践】：类型与依赖声明合一，替代冗长的重复声明
    2. 【生成器上下文依赖】：with sessionmaker() yield session 确保连接池零泄漏
    3. 【应用工厂模式 Application Factory】：让同一套路由既可在测试环境跑内存库，又能在生产跑 Postgres
    4. 【全链路 Request ID 中间件】：捕获高精度毫秒耗时与状态码，实现异常闭环追踪
    5. 【就绪探测与存活探针】：K8s 标配 /health/live 与 /health/ready 分离设计
"""

from collections.abc import Iterator
from contextlib import asynccontextmanager
import logging
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
from .schemas import DocumentInput, EventView, KnowledgeAnswer, QuestionInput, ReviewInput, TicketView
from .security import Actor, current_actor, load_identities, require_reviewer
from .workflow import TicketConflict, TicketNotFound, create_ticket, review_ticket, ticket_history, visible_ticket

logger = logging.getLogger("uvicorn.error.support_agent")


# ==============================================================================
# 1. 核心依赖定义：带生命周期清理的数据库会话
# ==============================================================================

def get_session(request: Request) -> Iterator[Session]:
    """
    【方法作用】：
        FastAPI 数据库会话提供者（带生命周期自动清理的生成器依赖）。
        每次 HTTP 请求进来时从连接池借用一个 Session，离开时 100% 自动归还并清理。

    【工作原理】：
        - yield 之前：通过 request.app.state.sessions() 借出连接；
        - yield session：注入给各个 Controller 接口使用；
        - yield 之后（离开 with 块）：SQLAlchemy 的 sessionmaker 会自动回滚任何未提交的事务，
          并把底层物理连接安全放回连接池，彻底杜绝数据库连接泄漏！

    【类似方法对比】：
        1. ✅ 生成器依赖 with sessions() as session: yield session（当前做法）
           - 优势：声明一次，全路由通用，自动化资源回收，发生未捕获异常时自动 rollback。
        2. ❌ 接口内部手动创建与关闭：
           - 代码：
               session = SessionLocal()
               try: ...
               finally: session.close()
           - 弊端：每个接口都得写一遍模板代码，且只要漏写一个 try...finally 就会耗尽数据库连接池引发宕机。
    """
    with request.app.state.sessions() as session:
        yield session


# ==============================================================================
# 2. Annotated 类型别名：现代 FastAPI 工业级标配
# ==============================================================================
# 为什么强烈推荐使用 typing.Annotated？
# - 旧写法：def answer(session: Session = Depends(get_session), actor: Actor = Depends(current_actor))
#   每次写接口参数都要拖着长长的一串 = Depends(...)，繁琐且容易在复制粘贴中出错；
# - 新写法：直接定义带语义的类型别名 Database, Identity, Reviewer，
#   在接口参数中直接声明 `session: Database, actor: Identity`，代码像自然语言一样清晰易读！

Database = Annotated[Session, Depends(get_session)]
Identity = Annotated[Actor, Depends(current_actor)]
Reviewer = Annotated[Actor, Depends(require_reviewer)]
IdempotencyKey = Annotated[str, Header(min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9._-]+$")]
SourceId = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")]


# ==============================================================================
# 3. 应用工厂函数 (Application Factory Pattern)
# ==============================================================================

def create_app(engine: Engine | None = None, identities: dict[str, Actor] | None = None) -> FastAPI:
    """
    【方法作用】：
        FastAPI 应用工厂函数。动态组装中间件、异常拦截器、生命周期和路由。

    【为什么使用应用工厂，而不是直接在文件顶层写 `app = FastAPI()`？】
        1. 测试隔离性：
           在跑自动化测试时（如 test_delivery.py），我们可以直接给 create_app(engine=mock_engine)
           传入临时的新建 SQLite 内存数据库，避免测试脏数据污染本地真实开发数据库；
        2. 多实例与多配置并存：
           允许在同一进程中以不同参数启动多个服务实例，天然适配集成测试与灰度发布。
    """
    actors = identities if identities is not None else load_identities()
    database = engine if engine is not None else build_engine()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """替代已废弃的 @app.on_event('startup'/'shutdown')"""
        try:
            yield
        finally:
            if engine is None:
                database.dispose()

    app = FastAPI(title="售后工单 Agent 实战", lifespan=lifespan)
    app.state.sessions = sessionmaker(database)
    app.state.identities = actors

    # --------------------------------------------------------------------------
    # 全链路追踪中间件：计算请求耗时、自动注入 Request ID
    # --------------------------------------------------------------------------
    @app.middleware("http")
    async def record_request(request: Request, call_next):
        """
        【中间件工作机制】：
            1. 在 call_next 执行前：生成唯一定位 ID (request_id)，记录精确起始纳秒时间戳；
            2. call_next(request)：将控制权交给下游的具体业务接口；
            3. 在 call_next 返回后：计算精准处理耗时（毫秒），并强制在响应头注入 `X-Request-ID`！
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
        
        route = getattr(request.scope.get("route"), "path", "<unmatched>")
        logger.info(
            "request_id=%s method=%s route=%s status=%s duration_ms=%.1f",
            request_id, request.method, route, status, (perf_counter() - started) * 1000,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    # --------------------------------------------------------------------------
    # 全局异常拦截器：业务异常统一映射为标准 HTTP 状态码
    # --------------------------------------------------------------------------
    @app.exception_handler(TicketNotFound)
    async def ticket_not_found(_request: Request, _error: TicketNotFound) -> JSONResponse:
        """工单不存在或跨租户未授权：映射为 404 Not Found"""
        return JSONResponse({"detail": "工单不存在"}, status_code=404)

    @app.exception_handler(TicketConflict)
    async def ticket_conflict(_request: Request, error: TicketConflict) -> JSONResponse:
        """幂等键冲突或状态机竞态排队冲突：映射为 409 Conflict"""
        return JSONResponse({"detail": str(error)}, status_code=409)

    # --------------------------------------------------------------------------
    # 健康检查探针（Kubernetes 生产部署标准）
    # --------------------------------------------------------------------------
    @app.get("/health/live")
    def live() -> dict[str, str]:
        """存活探针 (Liveness Probe)：检查 Web 进程自身是否存活"""
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready(session: Database) -> dict[str, str]:
        """
        就绪探针 (Readiness Probe)：
        不仅检查服务存活，还真实执行 SQL 探测所有核心数据表是否已经就绪。
        若 Alembic 迁移尚未执行完毕或数据库网络中断，立刻返回 503，防止流量打入未就绪的容器节点！
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
        """知识库检索问答接口：普通用户与客服分权检索"""
        return answer_question(session, actor, payload.question)

    @app.post("/tickets", status_code=201, responses={200: {"model": TicketView, "description": "幂等重放"}})
    def open_ticket(payload: QuestionInput, idempotency_key: IdempotencyKey, actor: Identity,
                    session: Database, response: Response) -> TicketView:
        """
        工单创建接口：
        - 首次创建返回 201 Created；
        - 重复幂等重放时自动修正返回 200 OK，并回传原有工单详情！
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
        """读取指定工单详情（强制执行租户与所有者安全可见性检查）"""
        return TicketView.model_validate(visible_ticket(session, actor, ticket_id))

    @app.post("/tickets/{ticket_id}/review")
    def review(ticket_id: str, payload: ReviewInput, actor: Reviewer, session: Database) -> TicketView:
        """人工审核工单（仅限 Reviewer 角色）：基于行级锁状态机原子迁移"""
        with session.begin():
            return TicketView.model_validate(review_ticket(session, actor, ticket_id, Status(payload.decision)))

    @app.get("/tickets/{ticket_id}/events")
    def events(ticket_id: str, actor: Reviewer, session: Database) -> list[EventView]:
        """查看工单审计流转日志"""
        return [EventView.model_validate(event) for event in ticket_history(session, actor, ticket_id)]

    @app.put("/knowledge/{source_id}", status_code=204)
    def put_document(source_id: SourceId, payload: DocumentInput, actor: Reviewer, session: Database) -> Response:
        """UPSERT 上传/更新知识库文档"""
        with session.begin():
            save_document(session, actor.tenant_id, source_id, payload)
        return Response(status_code=204)

    @app.delete("/knowledge/{source_id}", status_code=204)
    def delete_document(source_id: SourceId, actor: Reviewer, session: Database) -> Response:
        """物理下架知识库文档"""
        with session.begin():
            remove_document(session, actor.tenant_id, source_id)
        return Response(status_code=204)

    return app
