"""只验证公共框架，不替学习者编写订单业务接口或业务测试。"""

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app


def test_business_routes_are_left_empty():
    """文档可以访问，但没有预先实现用户准备练习的业务接口。"""
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()
        assert schema["paths"] == {}
        assert client.get("/docs").status_code == 200


def test_error_envelope_and_request_id():
    """框架错误必须能被前端 Axios 统一识别。"""
    with TestClient(create_app()) as client:
        response = client.get("/api/not-implemented")
        assert response.status_code == 404
        body = response.json()
        assert body["code"] == 404
        assert body["data"] is None
        assert body["request_id"] == response.headers["X-Request-ID"]


def test_framework_handles_business_http_exception():
    """这个临时路由只存在于测试，不会出现在交付的业务 API 中。"""
    app = create_app()

    @app.get("/_test-only")
    def test_only():
        raise HTTPException(409, "状态冲突")

    with TestClient(app) as client:
        response = client.get("/_test-only")
        assert response.status_code == 409
        assert response.json()["message"] == "状态冲突"


def test_engine_cleanup_even_if_model_client_close_fails(monkeypatch):
    import asyncio
    import pytest
    import app.main as main_module
    from app.core.config import Settings
    from sqlalchemy import create_engine

    disposed = []
    engine = create_engine("sqlite:///:memory:")
    original_dispose = engine.dispose
    def dispose():
        disposed.append(True)
        original_dispose()
    monkeypatch.setattr(engine, "dispose", dispose)
    monkeypatch.setattr(main_module, "build_engine", lambda settings: engine)
    class BrokenClient:
        async def close(self):
            raise RuntimeError("close failed")
    monkeypatch.setattr(main_module, "create_async_openai_client", lambda settings: BrokenClient())
    app = main_module.create_app(Settings(openai_api_key="unit-test-not-real", openai_model="test"))
    async def run_lifespan():
        async with app.router.lifespan_context(app):
            pass
    with pytest.raises(RuntimeError, match="close failed"):
        asyncio.run(run_lifespan())
    assert disposed == [True]
