# Genie SQL Dockerfile
# 使用多阶段构建减小镜像体积

# 阶段1：构建依赖
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（更快的 Python 包管理器）
RUN pip install --no-cache-dir uv

# 复制依赖配置
COPY pyproject.toml .
COPY README.md .

# 使用 uv 创建虚拟环境并安装依赖
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install -e .

# 阶段2：生产镜像
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 复制应用代码
COPY genie_sql/ ./genie_sql/
COPY server.py .
COPY start.sh .

# 创建日志目录
RUN mkdir -p /app/logs

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# 暴露端口
EXPOSE 1601

# 启动命令
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "1601", "--workers", "4"]
