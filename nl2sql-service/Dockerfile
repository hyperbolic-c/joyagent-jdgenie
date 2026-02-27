FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY nl2sql/ ./nl2sql/
COPY prompts/ ./prompts/

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 1601

# 启动命令
CMD ["python", "-m", "nl2sql.main"]
