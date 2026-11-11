"""
================================================================================
DAY 51 实战源码：FastAPI 企业级工程化与核心方法全解
================================================================================
配套讲义：daily_lessons/DAY_51_FastAPI工程化与方法全解.md

本文件在一个完整可运行的服务中，手把手演示企业级 FastAPI 的 7 大核心方法与对比：
    1. 【生命周期 lifespan】：替代已废弃的 @app.on_event，管理全局连接池 (app.state)
    2. 【传参四大金刚对比】：Path(路径) vs Query(问号查询) vs Body(JSON体) vs Header(请求头)
    3. 【依赖注入 Depends 对比】：普通 return 依赖(鉴权) vs 带 yield 的依赖(自动开关数据库会话)
    4. 【后台任务 BackgroundTasks】：接口秒回前端，后台异步执行耗时的文档向量化入库
    5. 【全局异常拦截器 @app.exception_handler】：统一包装 {code, msg, data} 并美化 422 报错
    6. 【模块化路由 APIRouter】：告别单文件面条代码，按业务模块拆分并挂载
    7. 【文件上传 UploadFile】：RAG 知识库上传文档的标准接口写法

运行方式：
    python day51_fastapi_engineering.py          # 自动运行内置自检测试（无需手动开浏览器，直接看全流程输出！）
    python day51_fastapi_engineering.py --serve  # 启动 8000 端口服务，浏览器访问 http://127.0.0.1:8000/docs
"""

import asyncio
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Generic, List, Optional, TypeVar

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# ==============================================================================
# 0. 企业级统一响应外壳（对标前端 axios 拦截器最喜欢的 { code, msg, data }）
# ==============================================================================

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    统一返回结构：
    - code: 0 表示成功，非 0 表示业务错误码
    - msg: 提示信息
    - data: 具体业务数据（支持泛型）
    """

    code: int = Field(default=0, description="业务状态码：0成功，非0失败")
    msg: str = Field(default="success", description="状态说明信息")
    data: Optional[T] = Field(default=None, description="响应数据载体")


# ==============================================================================
# 1. 应用生命周期管理：lifespan vs @app.on_event("startup")
# ==============================================================================
# ⚠️ 对比说明：
# - 旧写法 @app.on_event("startup") 已被 FastAPI 官方标记为 Deprecated（废弃）。
# - 新写法 @asynccontextmanager + lifespan：
#   把“启动初始化”和“关闭释放资源”合在一个函数里，用 yield 分界！


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # ---------------- 🚀 yield 之前：服务启动时执行 1 次 ----------------
    print("\n[Lifespan 启动] 正在初始化全局资源（大模型客户端、数据库连接池、向量库）...")
    # 把全局复用的对象挂载到 app.state 上，避免每次请求都重复创建！
    app.state.shared_resources = {
        "boot_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "vector_db_status": "ready",
        "ingested_docs": {},  # 模拟知识库文档状态表
    }
    print("[Lifespan 启动] 全局资源挂载到 app.state 完成！")

    yield  # 👈 服务运行期间一直停留在这里

    # ---------------- 🛑 yield 之后：服务关闭时自动执行 ----------------
    print("\n[Lifespan 关闭] 正在安全关闭连接池与清理缓存...")
    app.state.shared_resources.clear()
    print("[Lifespan 关闭] 资源已全部安全释放！")


app = FastAPI(
    title="AI Agent 企业级工程化后端模板",
    version="1.0.0",
    lifespan=app_lifespan,
)


# ==============================================================================
# 2. 全局异常拦截器：@app.exception_handler vs HTTPException
# ==============================================================================
# 对比说明：
# - HTTPException：在代码里随手抛错，但默认返回格式是 {"detail": "xxx"}，跟前端约定的 {code, msg, data} 不一致。
# - 自定义业务异常 + @app.exception_handler：无论在哪一层代码抛出 AgentBizError，
#   都会被自动拦截并包装成标准的 {code, msg, data: null} 返回给前端！


class AgentBizError(Exception):
    """自定义智能体业务异常（比如：Token 余额不足、大模型限流、知识库不存在）"""

    def __init__(self, code: int, msg: str, status_code: int = 400):
        self.code = code
        self.msg = msg
        self.status_code = status_code


@app.exception_handler(AgentBizError)
async def biz_error_handler(request: Request, exc: AgentBizError):
    """拦截所有 AgentBizError，返回统一 JSON 格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "msg": exc.msg, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    拦截你之前遇到过的 422 Unprocessable Entity 参数校验错误！
    把原本晦涩的英文数组报错，转成前端一眼能看懂的中文提示。
    """
    errors = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"])
        errors.append(f"参数 [{loc}] 不合法: {err['msg']}")
    return JSONResponse(
        status_code=422,
        content={
            "code": 42200,
            "msg": "请求参数校验未通过：" + "；".join(errors),
            "data": None,
        },
    )


# ==============================================================================
# 3. 依赖注入 Depends 详解：普通 return 依赖 vs 带 yield 的依赖
# ==============================================================================


# 3.1 普通 return 依赖：用于鉴权、提取当前登录用户
# 注意这里的 Header(...)：Python 变量名写 x_token，FastAPI 会自动去读请求头里的 "X-Token"！
async def get_current_user(
    x_token: str = Header(default="dev-token-001", description="用户鉴权 Token")
) -> Dict[str, Any]:
    """
    每次请求进来时自动检查请求头 X-Token。
    如果传了非法 token，直接抛出我们上面定义的 AgentBizError！
    """
    if x_token == "invalid":
        raise AgentBizError(code=40101, msg="登录凭证无效或已过期，请重新登录", status_code=401)
    return {"user_id": "u_888", "username": "小陈", "role": "ai_engineer", "token": x_token}


# 3.2 带 yield 的依赖：用于数据库 Session、外部连接（进入接口前打开，离开接口后自动关闭）
async def get_db_session():
    """
    【极其重要】：带 yield 的依赖函数！
    - yield 之前：在接口执行【前】运行（创建数据库连接）
    - yield 传出的值：注入给接口函数使用
    - finally 块（yield 之后）：在接口执行【后】100% 自动运行（哪怕接口内部报错了也会执行！）
    """
    print("  👉 [Depends Before] 打开数据库 Session 连接")
    fake_db = {"connected": True, "queries": []}
    try:
        yield fake_db
    finally:
        print("  👈 [Depends After] 接口执行完毕，自动关闭数据库 Session 连接")


# ==============================================================================
# 4. 模块化路由 APIRouter + 传参四大金刚 + BackgroundTasks
# ==============================================================================
# 对标前端：Express 的 express.Router()
# 真实项目里，下面这两个 router 会分别放在 routers/chat.py 和 routers/knowledge.py 文件中。

chat_router = APIRouter(prefix="/api/v1/sessions", tags=["1. 智能体对话模块"])
kb_router = APIRouter(prefix="/api/v1/kb", tags=["2. RAG 知识库模块"])


class ChatRequest(BaseModel):
    """POST JSON 请求体模型"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户提问内容")
    model_name: str = Field(default="gpt-6.1-sol", description="指定调用的大模型")


@chat_router.post("/{session_id}/messages", response_model=ApiResponse[Dict[str, Any]])
async def send_message(
    request: Request,
    # ① Path 路径参数：从 URL /api/v1/sessions/{session_id}/messages 中提取
    session_id: str = Path(..., min_length=3, description="会话唯一ID，如 sess_001"),
    # ② Query 查询参数：从 URL 问号后 ?enable_rag=true&top_k=3 中提取
    enable_rag: bool = Query(default=True, description="是否开启知识库检索"),
    top_k: int = Query(default=3, ge=1, le=10, description="检索召回条数"),
    # ③ Body 请求体参数：从 POST JSON Body 中提取
    payload: ChatRequest = Body(..., description="对话请求 JSON 体"),
    # ④ Header 请求头参数：从 HTTP Headers 中提取 X-Client-Version
    x_client_version: str = Header(default="web-1.0", description="前端客户端版本号"),
    # ⑤ Depends 依赖注入：自动执行鉴权 + 自动开关数据库会话
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Dict[str, Any] = Depends(get_db_session),
):
    """
    一个接口集齐 Path + Query + Body + Header + Depends 五大能力！
    """
    # 记录一次模拟数据库查询
    db["queries"].append(f"INSERT INTO messages (session_id) VALUES ('{session_id}')")

    # 从 app.state 读取 lifespan 启动时挂载的全局资源
    boot_time = request.app.state.shared_resources["boot_time"]

    return ApiResponse(
        code=0,
        msg="对话处理成功",
        data={
            "from_path_session_id": session_id,
            "from_query": {"enable_rag": enable_rag, "top_k": top_k},
            "from_body": payload.model_dump(),
            "from_header_version": x_client_version,
            "from_depends_user": current_user["username"],
            "server_boot_time": boot_time,
        },
    )


# ---------- 补充对比：不想建 BaseModel，只想从 JSON Body 读单个字段 ----------
@chat_router.post("/quick-rename")
async def quick_rename_session(
    # ⚠️ 关键对比：
    # - 如果写 new_title: str = Query(...) -> 从网址 ?new_title=xxx 取
    # - 如果写 new_title: str = Body(..., embed=True) -> 从 JSON {"new_title": "xxx"} 取！
    new_title: str = Body(..., embed=True, min_length=2, description="新会话标题")
):
    return ApiResponse(data={"renamed_to": new_title})


# ==============================================================================
# 5. 后台任务 BackgroundTasks + 文件上传 UploadFile（RAG 入库标准写法）
# ==============================================================================


async def background_parse_and_embed_doc(doc_id: str, filename: str, store: dict):
    """
    模拟耗时的后台文档解析、切块与向量化任务。
    它会在接口已经把响应返回给前端【之后】，在后台默默执行！
    """
    store[doc_id] = "parsing（正在解析切块...）"
    await asyncio.sleep(0.1)  # 模拟耗时操作
    store[doc_id] = f"completed（文件 {filename} 已完成向量化入库）"
    print(f"  ⚙️ [BackgroundTasks 后台任务完成] doc_id={doc_id}, 状态={store[doc_id]}")


@kb_router.post("/upload", response_model=ApiResponse[Dict[str, str]])
async def upload_knowledge_doc(
    request: Request,
    background_tasks: BackgroundTasks,
    # UploadFile 是 FastAPI 处理文件上传的标准类（底层使用异步流式读取，不怕大文件撑爆内存）
    # 配合表单字段用 Form(...)，注意：用了 File/Form 就不能同时用 JSON Body！
    file: UploadFile = File(..., description="上传的 PDF/TXT/MD 知识库文档"),
    kb_name: str = Form(default="默认知识库", description="所属知识库名称"),
):
    """
    上传文档接口：
    1. 读取文件基本信息；
    2. 用 background_tasks.add_task() 把耗时的向量化任务丢到后台；
    3. 0.01 秒立即给前端返回 doc_id，前端无需干等！
    """
    content_bytes = await file.read()  # 异步读取上传的文件字节
    doc_id = f"doc_{int(time.time() * 1000)}"
    docs_store = request.app.state.shared_resources["ingested_docs"]
    docs_store[doc_id] = "queued（排队中）"

    # 👇 核心方法：添加后台任务（接口返回后立即在后台执行）
    background_tasks.add_task(
        background_parse_and_embed_doc,
        doc_id,
        file.filename or "unnamed.txt",
        docs_store,
    )

    return ApiResponse(
        msg="文件上传成功，已转入后台异步向量化入库",
        data={
            "doc_id": doc_id,
            "filename": file.filename or "",
            "size_bytes": str(len(content_bytes)),
            "kb_name": kb_name,
            "current_status": docs_store[doc_id],
        },
    )


# 把拆分出去的子路由汇总挂载到主应用 app 上
app.include_router(chat_router)
app.include_router(kb_router)


# ==============================================================================
# 6. 内置自动化测试演示（直接运行本脚本即可看到全部请求与响应效果！）
# ==============================================================================


def run_self_test():
    """使用 FastAPI 官方 TestClient 在本地一键模拟前端发请求，验证上面所有方法"""
    from fastapi.testclient import TestClient

    print("=" * 75)
    print("开始运行 DAY 51 FastAPI 企业级工程化自检演示...")
    print("=" * 75)

    # with TestClient(app) 会自动触发上面定义的 app_lifespan 启动与关闭！
    with TestClient(app) as client:
        # 1. 测试 Path + Query + Body + Header + Depends
        print("\n【测试 1】综合调用 Path + Query + Body + Header + Depends(带yield)：")
        resp1 = client.post(
            "/api/v1/sessions/sess_2026/messages?enable_rag=true&top_k=5",
            json={"message": "请帮我总结 Q3 季度财报亮点", "model_name": "gpt-6.1-sol"},
            headers={"X-Token": "my-secret-token", "X-Client-Version": "react-web-2.0"},
        )
        print(f"  HTTP 状态码: {resp1.status_code}")
        print(f"  返回结果: {resp1.json()}")

        # 2. 测试全局自定义业务异常拦截器 (AgentBizError)
        print("\n【测试 2】传入错误 Token，触发全局异常拦截器 @app.exception_handler：")
        resp2 = client.post(
            "/api/v1/sessions/sess_2026/messages",
            json={"message": "你好"},
            headers={"X-Token": "invalid"},
        )
        print(f"  HTTP 状态码: {resp2.status_code}")
        print(f"  统一错误格式: {resp2.json()}")

        # 3. 测试美化后的 422 参数校验拦截器
        print("\n【测试 3】故意传错参数（top_k=999 超出 le=10），查看中文化的 422 报错：")
        resp3 = client.post(
            "/api/v1/sessions/sess_2026/messages?top_k=999",
            json={"message": ""},  # 同时违反 min_length=1
        )
        print(f"  HTTP 状态码: {resp3.status_code}")
        print(f"  中文化 422 报错: {resp3.json()}")

        # 4. 测试文件上传 UploadFile + 后台任务 BackgroundTasks
        print("\n【测试 4】上传知识库文件 UploadFile + 触发 BackgroundTasks 后台入库：")
        resp4 = client.post(
            "/api/v1/kb/upload",
            data={"kb_name": "企业财务制度库"},
            files={"file": ("差旅报销规范2026.txt", "报销标准：一线城市住宿上限500元/晚".encode("utf-8"), "text/plain")},
        )
        print(f"  HTTP 状态码: {resp4.status_code}")
        print(f"  接口秒回结果: {resp4.json()}")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn

        print("🚀 正在启动服务器，请在浏览器打开：http://127.0.0.1:8000/docs")
        uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        run_self_test()
