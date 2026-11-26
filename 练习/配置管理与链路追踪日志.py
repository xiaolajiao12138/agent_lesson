import os
import sys
import uuid
from contextvars import ContextVar
from functools import lru_cache

from fastapi import FastAPI, Request, Response
from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

app = FastAPI(title="链路追钟及配置中心集成服务")
# 创建上下文协程，无论有多少个异步协程并发跑，每个协程都拥有完全独立的request_id，不会混淆
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="system")


def setup_modern_logging():
    """配置现代结构化日志输出格式"""
    logger.remove()

    def inject_request_id(record):
        record["extra"]["req_id"] = request_id_ctx.get()
        # 直接给全局logger装上永久补丁，全项目任意文件from loguru import logger都能直接用

    logger.configure(patcher=inject_request_id)
    logger.add(
        sys.stdout,  # 日志输出到终端
        level="DEBUG",  # 指定最低输出级别，loguru输出级别  TRACE->DEBUG->INFO->SUCCESS->WARNING->ERROR->CRITICAL
        colorize=True,  # 将模板中的颜色标签转换为终端颜色
    )
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    logger.add(
        os.path.join(log_dir, "agent_app.log"),
        level="INFO",
        rotation="10 MB",  # 文件超出 10MB 自动新建一个
        retention="7 days",  # 只保留最近7天的日志，超过7天自动删除
        compression="zip",
        encoding="utf-8",
        enqueue=True,  # 开启异步队列无锁写入，绝不阻塞 web吞吐
    )


setup_modern_logging()


class AppSettings(BaseSettings):
    """系统全局强类型配置中心,从.env和系统环境变量中自动加载"""

    app_name: str = Field(default="myagentplatform", description="应用服务名称")
    server_port: int = Field(default=8080, le=65535, ge=1, description="端口范围1~65535")
    app_env: str = Field(default="development", description="运行环境,delopment/production/staging")
    is_debug: bool = Field(default=False, description="调试开关,自动识别True/False/0/1")
    api_key: str = Field(
        default="sk-test-mock-key-123456",
        description="大模型API KEY必填且必须是sk-开头",
    )
    base_url: str = Field(default="https://sub2api.starysp.top/v1", description="大模型网关地址")
    model_name: str = Field(default="gpt-6.1-sol", description="默认大模型名称")
    allowed_origins: list[str] = Field(default=["*"], description="允许跨域域名列表")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 忽略大小写(环境变量写API_KEY也能读取到api_key)
        extra="ignore",  # 忽略多余未知变量
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v.startswith("sk-"):
            raise ValueError("配置不合法,api_key必须以'sk-'开头")
        return v


@lru_cache
def get_settings() -> AppSettings:
    """
    单例缓存读取函数利用python标准库@lru_cache,保证整个生命周期只读取一次磁盘文件.env
    """
    return AppSettings()


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    incomming_id = request.headers.get("X-Request-ID")
    trace_id = incomming_id if incomming_id else f"req_{uuid.uuid4().hex[:8]}"

    # 将id绑定到当前的协程的上下文环境
    token = request_id_ctx.set(trace_id)
    try:
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        logger.info(f"请求完成，状态{response.status_code}")
        return response  # 将下游接口生成的响应继续返回客户端。
    except Exception as err:
        logger.exception(f"请求处理崩溃：{err}")
        raise  # 保留原始异常，交给 FastAPI 的异常处理机制。
    finally:
        # 重置上下文
        request_id_ctx.reset(token)


async def deep_agent_service(q: str):
    print(q)
    return f"针对 '{q}' 的智能分析回答"  # Day 22 的演示返回值。


@app.get("/api/v1/agent/query")
async def agent_query(q: str = "如何搭建智能体"):
    result = await deep_agent_service(q)
    return {"code": 0, "msg": "success", "data": {"answer": result}}


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn

        setting = get_settings()
        logger.info(f"{setting.server_port}")
        uvicorn.run(app, host="127.0.0.1", port=setting.server_port)
