# -*- coding: utf-8 -*-
# =====================
# 核心流程测试
# =====================
import asyncio

from nl2sql.llm import LLMClient
from nl2sql.models import LLMConfig
from nl2sql.rag import ColumnFilterModule


def test_column_filter_respects_table_id_list():
    """仅保留 modelCodeList 指定的数据表"""
    module = ColumnFilterModule(
        request_id="req-1",
        query="统计销售额",
        current_date_info="2024-01-01",
        table_id_list=["sales_order"],
        column_info=[
            {"modelCode": "sales_order", "schemaList": [{"columnId": "amount", "columnName": "销售额"}]},
            {"modelCode": "user_info", "schemaList": [{"columnId": "name", "columnName": "姓名"}]},
        ],
    )
    result = asyncio.run(module.batch_get_result())
    assert len(result) == 1
    assert result[0]["modelCode"] == "sales_order"


def test_column_filter_keyword_match_with_fallback():
    """字段无命中时回退全字段，避免空 schema 退化"""
    module = ColumnFilterModule(
        request_id="req-2",
        query="完全不相关关键字",
        current_date_info="2024-01-01",
        table_id_list=[],
        column_info=[
            {
                "modelCode": "sales_order",
                "schemaList": [
                    {"columnId": "order_id", "columnName": "订单ID"},
                    {"columnId": "amount", "columnName": "销售额"},
                ],
            }
        ],
    )
    result = asyncio.run(module.batch_get_result())
    assert len(result) == 1
    assert len(result[0]["schemaList"]) == 2


def test_llm_client_request_config_override_with_camel_case_fields():
    """请求级 llmConfig 能覆盖环境变量配置"""
    client = LLMClient(
        request_config=LLMConfig.model_validate(
            {
                "model": "gpt-4.1-mini",
                "apiKey": "key-123",
                "baseUrl": "https://example.com/v1",
                "temperature": 0.3,
                "topP": 0.7,
                "maxTokens": 2048,
            }
        )
    )
    config = client._get_config(model_type="nl2sql")
    assert config["model"] == "gpt-4.1-mini"
    assert config["api_key"] == "key-123"
    assert config["base_url"] == "https://example.com/v1"
    assert config["temperature"] == 0.3
    assert config["top_p"] == 0.7
