"""公共错误响应，与前端 Axios 的 {code, message, data} 约定一致。"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def register_exception_handlers(app: FastAPI) -> None:
    """注册处理函数；注册阶段不会执行处理函数的函数体。"""
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, headers=exc.headers,
            content={"code": exc.status_code, "message": str(exc.detail), "data": None,
                     "request_id": getattr(request.state, "request_id", None)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        first = exc.errors()[0]
        return JSONResponse(status_code=422,
            content={"code": 422, "message": f"参数校验失败：{first['msg']}", "data": None,
                     "request_id": getattr(request.state, "request_id", None)})
