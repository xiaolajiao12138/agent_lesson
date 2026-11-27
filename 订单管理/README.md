# 订单管理

**前端页面已完成，Python 后端仅完成公共框架，业务接口有意留空，供你自己练习。**

## 前端页面

- 登录：输入账号密码、填充演示账号、失败反馈、客户/管理员角色导航。
- 智能客服：输入问题、查看回复、转人工表单、关联订单、查看及刷新申请处理结果。
- 管理员订单查询：关键词、状态筛选、分页、订单详情。
- 审批中心：待审批/通过/拒绝筛选、客户问题、关联订单、处理记录、审批意见及确认。
- 按桌面网页使用；Axios 参照 new_ad_web 的 VAxios 与 transform hooks 分层。

## 启动前端

在本项目目录运行 `.\启动前端.ps1`，或执行：

```powershell
Set-Location "C:\Users\Administrator\Desktop\agent学习\订单管理\frontend"
npm install
npm run dev
```

打开 http://127.0.0.1:5174 。Node.js 要求 22.12+。

| 演示角色 | 账号 | 密码 |
| --- | --- | --- |
| 客户 | customer | 123456 |
| 管理员 | admin | 123456 |

customer2 / 123456 可用于体验客户之间的数据隔离。以上仅是前端演示凭证，不是后端认证。

体验顺序：客户登录 → 提问“我想申请退货” → 转人工并关联订单 → 退出 → 管理员登录 → 审批中心处理 → 退出 → 客户登录 → 在原对话刷新申请进度。

**默认演示模式不会调用 Python 业务接口，也不会调用大模型。** 页面顶部和回复正文都有演示标识。演示数据保存在当前浏览器 localStorage，不同浏览器不共享。不要把本地演示权限当成后端安全控制。

## 启动后端框架

首次创建独立环境：

```powershell
Set-Location "C:\Users\Administrator\Desktop\agent学习\订单管理\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

之后在项目目录运行 `.\启动后端.ps1`，或在 backend 中执行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
```

接口文档：http://127.0.0.1:8001/docs 。目前没有业务操作是预期结果，登录、订单、问答、转人工和审批接口都留给你实现。

## 真实大模型配置

加载优先级由低到高：学习仓库根目录 `.env` → 本项目 `.env` → `backend/.env` → 当前进程环境变量。

当前自动复用你的学习仓库真实模型配置，读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL_NAME`。模板 `backend/.env.example` 不自动加载；独立部署时复制并填写自己的配置。

应用启动后，`request.app.state.llm_client` 是真实 AsyncOpenAI 客户端，模型名在 `request.app.state.settings.openai_model`。配置不完整时客户端为 None。模型调用需要你自行在问答业务中实现，框架启动不会自动发送付费请求，不会生成伪造回答。

密钥只在 Python 后端读取；不要把密钥写到前端或任何 VITE_ 变量。

## 切换到自己的接口

创建 `frontend/.env.local`：

```ini
VITE_DEMO_MODE=false
VITE_API_BASE_URL=/api
VITE_BACKEND_TARGET=http://127.0.0.1:8001
```

重启前端。此时请求只走 Axios，不会在后端报错时回退到演示数据。前端所需接口见 [接口练习约定](docs/接口练习约定.md)，业务类型见 `frontend/src/types/index.ts`。

统一响应：`{ "code": 200, "message": "操作成功", "data": ... }`。Axios 默认返回其中的 data。

## 阅读顺序

```text
frontend/src/
  views/                 登录、客服、订单、审批
  api/index.ts           请求地址、参数及演示/真实模式切换
  utils/http/axios/      VAxios、转换钩子、Token、错误处理
  services/demo.ts       仅用于前端页面体验的本地适配层
  stores/                登录状态和提示信息
  router/                页面路由和角色导航
backend/app/
  core/config.py         环境变量加载、布尔值解析
  main.py                应用工厂、生命周期、中间件
  core/llm.py            真实模型客户端工厂
  db.py                  Engine、Session 工厂、Depends、Base
  api/router.py          空业务路由入口
  api/routes/            等你写接口
  models/                等你定义业务表
  schemas/base.py        公共响应模型
  services/              等你实现业务服务
```

Axios 参考原文件：`new_ad_web/web/src/utils/http/axios/Axios.ts` 和 `index.ts`。移除了广告上传、缓存、埋点和业务 Store 等非本项目依赖。

## 验证

在 backend 运行 `.\.venv\Scripts\python.exe -m pytest -q`。
在 frontend 运行 `npm test` 和 `npm run build`。

SQLite 文件在真正访问数据库时才会创建；没有预置业务表、建表和迁移脚本，建模及 SQL 由你练习。
