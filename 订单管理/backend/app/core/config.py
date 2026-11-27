"""配置初始化：复用学习仓库的大模型配置，绝不把 API Key 传给浏览器。

知识对应：环境变量、dataclass、Path、字典覆盖、布尔值解析。
优先级由低到高：学习仓库 .env → 项目 .env → backend/.env → 当前进程环境变量。
"""
from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


def parse_bool(value: str) -> bool:
    """显式解析字符串；不能用 bool('False')，因为非空字符串总为 True。"""
    normalized = value.strip().casefold()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("布尔配置只能使用 true/false、1/0、yes/no、on/off")


@dataclass(frozen=True, slots=True)
class Settings:
    """frozen=True 表示加载后不可随意改配置；repr=False 避免打印对象时暴露密钥。"""
    app_name: str = "订单管理 · 后端框架"
    debug: bool = False
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data/orders.db').as_posix()}"
    openai_api_key: str = field(default="", repr=False)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = ""
    model_timeout: float = 60.0
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5174", "http://localhost:5174")

    @property
    def model_configured(self) -> bool:
        """只暴露配置是否齐全，不暴露密钥正文。不会发起付费模型请求。"""
        return bool(self.openai_api_key and self.openai_model)

    @classmethod
    def from_env(cls) -> "Settings":
        values: dict[str, str] = {}
        for path in (PROJECT_DIR.parent / ".env", PROJECT_DIR / ".env", BACKEND_DIR / ".env"):
            if path.is_file():
                values.update({key: value for key, value in dotenv_values(path).items() if value is not None})
        values.update(os.environ)
        defaults = cls()
        return cls(
            app_name=values.get("ORDER_APP_NAME", defaults.app_name),
            debug=parse_bool(values.get("ORDER_DEBUG", "false")),
            database_url=values.get("ORDER_DATABASE_URL", defaults.database_url),
            openai_api_key=values.get("OPENAI_API_KEY", ""),
            openai_base_url=values.get("OPENAI_BASE_URL", defaults.openai_base_url).rstrip("/"),
            openai_model=values.get("OPENAI_MODEL_NAME", values.get("OPENAI_MODEL", "")),
            model_timeout=float(values.get("ORDER_MODEL_TIMEOUT", "60")),
            cors_origins=tuple(origin.strip() for origin in values.get("ORDER_CORS_ORIGINS", ",".join(defaults.cors_origins)).split(",") if origin.strip()),
        )
