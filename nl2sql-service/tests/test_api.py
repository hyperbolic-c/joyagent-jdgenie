# -*- coding: utf-8 -*-
# =====================
# API 测试
# =====================
import pytest
from fastapi.testclient import TestClient

from nl2sql.main import app

client = TestClient(app)


def test_health_check():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "NL2SQL Service"


def test_nl2sql_endpoint_validation():
    """测试 NL2SQL 接口参数验证"""
    # 缺少必需参数
    response = client.post("/v1/tool/nl2sql", json={})
    assert response.status_code == 422  # 验证错误


def test_nl2sql_endpoint_empty_query():
    """测试空查询处理"""
    response = client.post("/v1/tool/nl2sql", json={
        "requestId": "req-123",
        "query": "",
        "currentDateInfo": "2024-01-01",
        "modelCodeList": [],
        "schemaInfo": [],
        "stream": False
    })
    # 应该返回错误响应
    assert response.status_code == 200
    result = response.json()
    assert "err_msg" in result or result.get("code") == 200
