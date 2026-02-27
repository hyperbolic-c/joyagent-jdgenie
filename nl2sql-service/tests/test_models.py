# -*- coding: utf-8 -*-
# =====================
# 模型测试
# =====================
import pytest

from nl2sql.models import LLMConfig, NL2SQLRequest, NL2SQLResponse, NL2SQLData


def test_llm_config():
    """测试 LLM 配置模型"""
    config = LLMConfig(
        model="gpt-4.1",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        temperature=0.5,
        top_p=0.9
    )
    assert config.model == "gpt-4.1"
    assert config.api_key == "test-key"
    assert config.temperature == 0.5


def test_nl2sql_request():
    """测试 NL2SQL 请求模型"""
    request = NL2SQLRequest(
        requestId="req-123",
        query="测试查询",
        currentDateInfo="2024-01-01",
        modelCodeList=["table1"],
        schemaInfo=[],
        stream=True,
        dbType="mysql"
    )
    assert request.request_id == "req-123"
    assert request.query == "测试查询"
    assert request.dialect == "mysql"


def test_nl2sql_request_with_llm_config():
    """测试带 LLM 配置的请求模型"""
    llm_config = LLMConfig(model="gpt-4")
    request = NL2SQLRequest(
        requestId="req-123",
        query="测试查询",
        currentDateInfo="2024-01-01",
        modelCodeList=[],
        schemaInfo=[],
        llmConfig=llm_config
    )
    assert request.llm_config is not None
    assert request.llm_config.model == "gpt-4"


def test_nl2sql_request_with_camel_case_llm_config():
    """测试 llmConfig 的 camelCase 字段兼容"""
    request = NL2SQLRequest.model_validate(
        {
            "requestId": "req-123",
            "query": "测试查询",
            "currentDateInfo": "2024-01-01",
            "modelCodeList": [],
            "schemaInfo": [],
            "llmConfig": {
                "model": "gpt-4.1",
                "apiKey": "test-key",
                "baseUrl": "https://api.openai.com/v1",
                "temperature": 0.2,
                "topP": 0.8,
                "maxTokens": 1024,
            },
        }
    )
    assert request.llm_config is not None
    assert request.llm_config.api_key == "test-key"
    assert request.llm_config.base_url == "https://api.openai.com/v1"
    assert request.llm_config.top_p == 0.8
    assert request.llm_config.max_tokens == 1024


def test_nl2sql_response():
    """测试 NL2SQL 响应模型"""
    data = NL2SQLData(query="问题", nl2sql="SELECT * FROM table")
    response = NL2SQLResponse(
        code=200,
        requestId="req-123",
        status="finished",
        data=[data]
    )
    assert response.code == 200
    assert len(response.data) == 1
    assert response.data[0].nl2sql == "SELECT * FROM table"
