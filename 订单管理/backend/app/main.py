"""订单管理应用工厂：只装配基础框架，不实现业务接口。

阅读顺序：core/config.py → create_app() → lifespan() → db.get_session()。
启动：python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
"""
from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from .api.router import router
from .core.config import Settings
from .core.errors import register_exception_handlers
from .core.llm import create_async_openai_client
from .db import build_engine

logger = logging.getLogger("uvicorn.error.order_management")


def create_app(settings: Settings | None = None) -> FastAPI:
    """工厂每调用一次创建一个应用；测试可以注入独立 Settings。"""
    settings = settings or Settings.from_env()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 客户端初始化不会产生模型请求。配置不齐全时保持 None，业务接口自行处理。
        client = create_async_openai_client(settings) if settings.model_configured else None
        app.state.llm_client = client
        try:
            yield
        finally:
            try:
                if client is not None:
                    await client.close()
            finally:
                # 即使模型客户端关闭失败，也必须释放数据库连接池。
                engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan,
                  description="仅提供后端框架。业务路由有意留空，请按 docs/接口练习约定.md 自行实现。")
    app.state.settings = settings
    app.state.sessions = sessionmaker(bind=engine, expire_on_commit=False)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
    register_exception_handlers(app)

    @app.middleware("http")
    async def trace_request(request: Request, call_next):
        request_id = uuid4().hex
        request.state.request_id = request_id
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("未处理异常 request_id=%s", request_id)
            response = JSONResponse(status_code=500,
                content={"code": 500, "message": "服务内部错误，请根据请求编号排查", "data": None,
                         "request_id": request_id})
        response.headers["X-Request-ID"] = request_id
        logger.info("request_id=%s method=%s status=%s duration_ms=%.1f", request_id,
                    request.method, response.status_code, (perf_counter() - started) * 1000)
        return response

    # 空路由不产生业务接口；你实现接口后在 api/router.py 注册即可。
    app.include_router(router, prefix="/api")
    return app
