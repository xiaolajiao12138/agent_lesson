"""
================================================================================
DAY 22 实战源码：企业级强类型配置中心与链路追踪日志系统
================================================================================
配套讲义：daily_lessons/DAY_22_配置管理与链路追踪日志.md

本文件系统演示企业级 Python / Agent 开发必备的配置与日志最佳工程实践：
    1. 【os.getenv 踩坑现场】：展示类型转换失误（如 "false" 变成 True）与漏填隐患
    2. 【pydantic-settings 强类型配置】：强类型自动转换、必填校验、@lru_cache 内存单例
    3. 【loguru 生产级日志系统】：开箱即用彩色高亮、代码行号定位、文件切割与保留
    4. 【全链路 Request ID 穿透实战】：
        - 使用 Python 标准库 contextvars.ContextVar 实现协程间上下文隔离（对标 Node.js AsyncLocalStorage）
        - 编写 FastAPI 纯净中间件，为每个 HTTP 请求打上唯一 Request ID
        - 通过 loguru patcher 机制，让后续所有多层函数调用中的日志全自动附带 [req_xxx] 标签！

运行方式：
    python day22_settings_and_logging.py          # 运行全套自检对比演示（直观查看控制台日志与配置）
    python day22_settings_and_logging.py --serve  # 启动 8000 端口服务，可在浏览器中发请求测试
"""

import asyncio
from contextvars import ContextVar
from functools import lru_cache
import io
import os
import sys
import time
from typing import Any, Dict, List, Optional
import uuid

# 适配 Windows 控制台 UTF-8 输出，防止 Emoji 字符导致 gbk 编码报错
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 引入 FastAPI 核心组件
from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 尝试引入 loguru，若未安装则提供明确提示
try:
    from loguru import logger
except ImportError:
    print("❌ 缺少依赖库 loguru，请在终端执行：pip install loguru")
    sys.exit(1)


# ==============================================================================
# 1. 对比演示：os.getenv() 的典型隐患 vs pydantic-settings
# ==============================================================================

def demo_os_getenv_pitfalls():
    """
    演示传统 os.getenv 极其容易引发的逻辑 BUG
    """
    print("=" * 75)
    print("【对比 1】传统 os.getenv() 的类型转换陷阱演示")
    print("=" * 75)

    # 模拟外部环境设置 DEBUG 为 "False" 字符串
    os.environ["MOCK_DEBUG"] = "False"
    os.environ["MOCK_PORT"] = "8080"

    # ❌ 经典踩坑：在 Python 中，非空字符串 bool("False") 的结果是 True！
    is_debug_bad = bool(os.getenv("MOCK_DEBUG", "True"))
    print(f"  ❌ 错误做法：bool(os.getenv('MOCK_DEBUG')) -> 得到结果: {is_debug_bad} (期望为 False，却得到了 True！)")

    # ❌ 经典踩坑：必须手动做大量类型强转，如果环境变量拼错成了非数字字符串，启动直接抛 ValueError 崩掉
    port_bad = int(os.getenv("MOCK_PORT", "8000"))
    print(f"  ⚠️ 手动转换: int(os.getenv('MOCK_PORT')) -> {port_bad} (缺乏范围检查，比如传了 -1 无法拦截)")


# ==============================================================================
# 2. pydantic-settings 现代强类型配置中心（标准最佳实践）
# ==============================================================================

class AppSettings(BaseSettings):
    """
    系统全局强类型配置中心（从 .env 和系统环境变量中自动加载）
    """
    # 1. 必填字段与服务基础配置
    app_name: str = Field(default="MyAgentPlatform", description="应用服务名称")
    app_env: str = Field(default="development", description="运行环境: development / staging / production")
    server_port: int = Field(default=8000, ge=1, le=65535, description="端口范围 1~65535")
    is_debug: bool = Field(default=False, description="调试模式开关（自动识别 'true'/'false'/'1'/'0'）")

    # 2. 大模型与第三方凭据配置
    api_key: str = Field(default="sk-test-mock-key-123456", description="大模型 API Key（必填且须以 sk- 开头）")
    base_url: str = Field(default="https://sub2api.starysp.top/v1", description="接口网关地址")
    model_name: str = Field(default="gpt-6.1-sol", description="默认大模型名称")

    # 3. 复杂类型：自动将逗号分隔或 JSON 格式解析为 Python List
    allowed_origins: List[str] = Field(default=["*"], description="允许的跨域域名列表")

    # 4. 配置映射规则
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 忽略大小写（系统环境变量写 API_KEY 也能读取到 api_key）
        extra="ignore",        # 忽略多余的未知变量
    )

    # 5. 自定义高级校验器：校验 API Key 安全规则
    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v.startswith("sk-"):
            raise ValueError("配置不合法：api_key 必须以 'sk-' 开头！")
        return v


@lru_cache
def get_settings() -> AppSettings:
    """
    单例缓存读取函数（对标前端的单例模式）
    利用 Python 标准库 @lru_cache，保证整个进程生命周期中只读取解析一次磁盘上的 .env
    """
    return AppSettings()


# ==============================================================================
# 3. loguru 日志系统配置与 ContextVar 链路追踪绑定
# ==============================================================================

# 创建协程上下文变量（ContextVar）：
# 这类似于前端 React 的 Context 或 Node.js 的 AsyncLocalStorage，
# 无论有多少个异步协程并发跑，每个协程都拥有完全独立的 request_id 副本，绝不混淆！
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="system")


def setup_modern_logging():
    """
    配置现代结构化日志输出格式
    """
    # 1. 移除 loguru 默认的简陋处理器
    logger.remove()

    # 2. 编写自定义 patcher：为每一条日志自动附带当前协程的 request_id
    def inject_request_id(record):
        # 从 contextvars 提取当前请求的 ID
        record["extra"]["req_id"] = request_id_ctx.get()

    # 将 patcher 安装到全局 logger
    configured_logger = logger.patch(inject_request_id)

    # 3. 添加控制台彩色输出处理器
    # 格式模板中加入 <magenta>[{extra[req_id]}]</magenta>，使每行日志都有独特的粉色追踪标识！
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<magenta>[{extra[req_id]}]</magenta> - "
        "<level>{message}</level>"
    )

    configured_logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG",
        colorize=True,
    )

    # 4. 可选：同时写入本地持久化文件（演示开箱即用的自动按天轮转与压缩存储）
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    configured_logger.add(
        os.path.join(log_dir, "agent_app.log"),
        format=log_format,
        level="INFO",
        rotation="10 MB",     # 文件超过 10MB 自动新建一个
        retention="7 days",    # 只保留最近 7 天的日志，过期自动删除
        compression="zip",     # 旧日志自动打包压缩为 zip 省空间
        encoding="utf-8",
        enqueue=True,          # 开启异步队列无锁写入，绝不阻塞 Web 吞吐
    )

    return configured_logger


# 初始化配置全局 logger
app_logger = setup_modern_logging()


# ==============================================================================
# 4. FastAPI 搭建与 Trace ID 拦截中间件
# ==============================================================================

app = FastAPI(title="链路追踪与配置中心集成服务")


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """
    【链路追踪核心中间件】：
    1. 读取前端传入的 X-Request-ID（若没有则由服务端自动生成一个短 UUID）
    2. 将其设置进 contextvars 协程上下文
    3. 调用下游接口
    4. 将 X-Request-ID 附带到 HTTP 响应头传回前端，方便前端发生异常时拿着 ID 找后端查日志！
    """
    incoming_id = request.headers.get("X-Request-ID")
    trace_id = incoming_id if incoming_id else f"req_{uuid.uuid4().hex[:8]}"

    # 将其绑定到当前协程的上下文环境
    token = request_id_ctx.set(trace_id)

    app_logger.info(f"👉 HTTP 请求进入: {request.method} {request.url.path}")
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000
        # 将请求 ID 注入回响应头，前端可直接通过 response.headers.get('x-request-id') 拿到
        response.headers["X-Request-ID"] = trace_id
        app_logger.info(f"👈 HTTP 请求完成: 状态码={response.status_code}, 耗时={process_time_ms:.2f}ms")
        return response
    except Exception as exc:
        app_logger.exception(f"💥 请求处理崩溃: {exc}")
        raise
    finally:
        # 重置上下文，养成内存安全的好习惯
        request_id_ctx.reset(token)


# 模拟底层业务层函数（深层调用），证明完全不需要手动传递 trace_id，日志也能自动带上！
async def deep_agent_service(query: str):
    app_logger.debug("正在解析用户意图与 Prompt 模板...")
    await asyncio.sleep(0.05)  # 模拟网络 IO
    app_logger.info(f"调用工具链完成，输入问题: '{query}'")
    return f"针对 '{query}' 的智能分析回答"


@app.get("/api/v1/agent/query")
async def agent_query(q: str = "如何搭建智能体？"):
    app_logger.info(f"API Controller 接收到用户参数: q={q}")
    # 调用深层业务函数
    result = await deep_agent_service(q)
    app_logger.info("业务逻辑处理完毕，准备返回响应")
    return {"code": 0, "msg": "success", "data": {"answer": result}}


@app.get("/api/v1/config/inspect")
async def inspect_config():
    """查看当前加载生效的强类型配置"""
    settings = get_settings()
    app_logger.info("正在调阅全局系统配置")
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "server_port": settings.server_port,
        "is_debug": settings.is_debug,
        "model_name": settings.model_name,
        "base_url": settings.base_url,
    }


# ==============================================================================
# 5. 全流程本地自动化自检演示（并发验证）
# ==============================================================================

def run_self_test():
    """
    一键运行全套测试：演示配置强类型校验与 3 个并发请求下，日志自动穿透携带 [req_xxx] 的效果
    """
    demo_os_getenv_pitfalls()

    print("\n" + "=" * 75)
    print("【对比 2】pydantic-settings 强类型解析与单例验证")
    print("=" * 75)
    settings = get_settings()
    print(f"  ✅ 成功获取强类型配置单例: {settings.app_name} (Port: {settings.server_port}, Debug: {settings.is_debug})")
    print(f"  ✅ 目标模型: {settings.model_name}, 网关: {settings.base_url}")

    print("\n" + "=" * 75)
    print("【实战 3】FastAPI 多并发请求下，Request ID 自动穿透日志验证")
    print("=" * 75)
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 模拟用户 A 发起提问
    print("\n▶ 模拟客户端 A 发送请求（传入自定义 X-Request-ID: user-A-001）：")
    resp_a = client.get("/api/v1/agent/query?q=什么是LangGraph", headers={"X-Request-ID": "user-A-001"})
    print(f"  客户端 A 收到响应头 X-Request-ID: {resp_a.headers.get('x-request-id')}")

    # 模拟用户 B 发起提问（不传请求头，由服务端自动分配唯一 UUID）
    print("\n▶ 模拟客户端 B 发送请求（由系统自动分配 Request ID）：")
    resp_b = client.get("/api/v1/agent/query?q=什么是FastAPI依赖注入")
    print(f"  客户端 B 收到响应头 X-Request-ID: {resp_b.headers.get('x-request-id')}")

    print("\n🎉 观察上方控制台日志输出：")
    print("👉 每一条日志都清晰带着各自的 [user-A-001] 或 [req_xxxxxxxx] 标签！")
    print("👉 无论代码调用嵌套了多少层（Controller -> Service -> Tool），全流程自动绑定，彻底消灭并发排错盲区！")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn
        settings = get_settings()
        app_logger.info(f"🚀 启动生产级 Web 服务，监听端口: {settings.server_port}")
        uvicorn.run(app, host="127.0.0.1", port=settings.server_port)
    else:
        run_self_test()
