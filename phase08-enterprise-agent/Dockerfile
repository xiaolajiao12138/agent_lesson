# 企业实战第 7 课｜把 API 和迁移代码打包成可运行镜像。
# FROM 选择基础环境；slim 减少预装系统组件，应用依赖在后续步骤安装。
FROM python:3.12-slim

# WORKDIR 设置后续构建命令及容器启动时的工作目录，也决定 SQLite 相对路径的基准。
WORKDIR /app
# 两个变量分别控制 Python 字节码文件生成和标准输出缓冲，便于容器日志及时显示。
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# 依赖文件先复制，业务代码变化时可以复用依赖层。
COPY requirements.txt .
# RUN 在镜像构建阶段执行，--no-cache-dir 减少 pip 缓存进入镜像。
RUN pip install --no-cache-dir -r requirements.txt
# COPY 把迁移配置和应用源码放进镜像；数据、凭证通过卷或环境变量提供。
COPY alembic.ini .
COPY migrations ./migrations
COPY support_agent ./support_agent

# 使用指定的非 root 用户运行进程，容器挂载目录需提供相应读写权限。
USER 10001:10001
# EXPOSE 声明容器服务端口，实际宿主机映射由 compose.yaml 的 ports 设置。
EXPOSE 8000
# CMD 在容器启动时执行；--factory 调用 create_app()，0.0.0.0 在容器内部监听。
# Compose 的 migrate 服务可通过 command 覆盖此默认命令，改为执行 Alembic。
CMD ["python", "-m", "uvicorn", "support_agent.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
