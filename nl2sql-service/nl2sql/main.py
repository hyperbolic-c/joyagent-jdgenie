# -*- coding: utf-8 -*-
# =====================
# FastAPI 入口
# =====================
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nl2sql.api import router
from nl2sql.utils import setup_logging

# 配置日志
log_path = os.getenv("LOG_PATH", "logs/nl2sql.log")
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_path=log_path, level=log_level)

# 创建 FastAPI 应用
app = FastAPI(
    title="NL2SQL Service",
    description="独立的 NL2SQL 算法服务",
    version="1.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/v1/tool")


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "NL2SQL Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "nl2sql-service"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "1601"))
    uvicorn.run(app, host="0.0.0.0", port=port)
