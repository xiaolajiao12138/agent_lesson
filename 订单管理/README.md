# 订单管理

**前端页面已完成，所有业务请求统一通过 Axios 访问 Python 后端。后端业务接口留空，供你自行练习实现。**

## 页面

- 登录：使用后端创建的账号，身份和角色以登录接口返回为准。
- 智能客服：向问答接口发送问题，按接口返回展示回答或转人工入口。
- 订单查询：请求订单列表、筛选结果和订单详情。
- 审批中心：请求服务申请及操作记录，向审批接口提交处理意见。

没有内置账号、示例订单、示例工单或固定模型回复。没有模式切换开关或请求失败后回退本地数据的分支。

## 启动

在项目目录运行 `.\启动前端.ps1`，打开 http://127.0.0.1:5174 。Node.js 要求 22.12+。

或在 frontend 目录运行：

```powershell
npm install
npm run dev
```

在项目目录运行 `.\启动后端.ps1`。接口文档为 http://127.0.0.1:8001/docs 。

首次创建后端独立环境时，在 backend 中运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

**目前后端没有登录等业务接口，所以提交登录会收到 404；未启动后端时会收到连接错误。这些错误来自实际请求，不会被本地数据掩盖。** 请先实现登录和当前身份接口，再继续联调其他页面。

## 前端连接配置

默认通过 Vite 将 `/api` 代理至 `http://127.0.0.1:8001`。如果要修改地址，创建 `frontend/.env.local`：

```ini
VITE_API_BASE_URL=/api
VITE_BACKEND_TARGET=http://127.0.0.1:8001
```

修改后重启前端。所有页面请求都在 `frontend/src/api/index.ts` 中声明。

接口字段与路径见 [接口练习约定](docs/接口练习约定.md)。成功响应统一为 `{ "code": 200, "message": "操作成功", "data": ... }`，Axios 默认解包其中的 data。

新版首次加载时，会清理本项目旧版的体验数据、聊天缓存和体验登录 Token。真实登录 Token 与其他应用的存储保留。当前聊天记录只保留在当前页面内存中，不会读取旧的本地回复。

## 真实大模型配置

配置优先级从低到高：学习仓库根目录 `.env` → 本项目 `.env` → `backend/.env` → 当前进程环境变量。

自动复用 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL_NAME`。模板 `backend/.env.example` 不自动加载。

应用启动后，真实 AsyncOpenAI 客户端位于 `request.app.state.llm_client`，模型名位于 `request.app.state.settings.openai_model`。配置不完整时客户端为 None。框架初始化不会主动发送付费请求；问答接口和模型调用仍由你编写。

密钥仅在 Python 后端读取，不得放入前端或任何 VITE_ 变量。

## 阅读顺序

```text
frontend/src/
  views/                 登录、客服、订单、审批页面
  api/index.ts           真实请求地址与类型声明
  utils/http/axios/      VAxios、请求/响应转换、Token 与错误处理
  utils/token.ts         登录 Token 和旧缓存迁移
  stores/                当前身份与提示信息
  router/                页面导航与角色限制
backend/app/
  core/config.py         配置加载
  main.py                应用工厂、生命周期、中间件
  core/llm.py            真实模型客户端
  db.py                  Engine、Session、Depends、Base
  api/router.py          待注册的业务路由入口
  api/routes/            待实现的接口
  models/                待定义的业务表
  schemas/base.py        统一响应结构
  services/              待实现的业务服务
```

Axios 结构参考 new_ad_web/web/src/utils/http/axios/Axios.ts 和 index.ts。后端认证、数据权限、SQL、幂等、状态机及业务测试由你练习。

## 验证

在 frontend 中运行 `npm test` 和 `npm run build`。
在 backend 中运行 `.\.venv\Scripts\python.exe -m pytest -q`。
