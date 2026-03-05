# -*- coding: utf-8 -*-
# =====================
# 核心流程测试
# =====================
import asyncio

from nl2sql.core import NL2SQLAgent
from nl2sql.llm import LLMClient
from nl2sql.models import LLMConfig, NL2SQLRequest
from nl2sql.rag import ColumnFilterModule


def test_column_filter_two_stage_flow():
    """验证两阶段流程：先选表，再做字段筛选。"""
    module = ColumnFilterModule(
        request_id="req-1",
        query="统计销售额",
        current_date_info="2024-01-01",
        table_id_list=[],
        column_info=[
            {"modelCode": "sales_order", "schemaList": [{"columnId": "amount", "columnName": "销售额"}]},
            {"modelCode": "user_info", "schemaList": [{"columnId": "name", "columnName": "姓名"}]},
            {"modelCode": "inventory", "schemaList": [{"columnId": "stock", "columnName": "库存"}]},
        ],
    )
    module.need_filter_table_min_length = 1

    class FakeLLMClient:
        async def chat(self, model_type="nl2sql", **kwargs):
            if model_type == "table_filter":
                yield "[1, 3]"
                return
            # column_filter
            yield """```json
{"relatedFlag": true, "columnIndexes": [1]}
```"""

    module.llm_client = FakeLLMClient()
    result = asyncio.run(module.batch_get_result())
    assert len(result) == 2
    assert result[0]["modelCode"] == "sales_order"
    assert result[1]["modelCode"] == "inventory"


def test_column_filter_keeps_default_recall():
    """字段筛选应保留 defaultRecall=1 的字段。"""
    module = ColumnFilterModule(
        request_id="req-2",
        query="只看订单",
        current_date_info="2024-01-01",
        table_id_list=[],
        column_info=[
            {
                "modelCode": "sales_order",
                "schemaList": [
                    {"columnId": "order_id", "columnName": "订单ID", "defaultRecall": 1},
                    {"columnId": "amount", "columnName": "销售额"},
                ],
            }
        ],
    )
    module._is_first_filter_table = False

    class FakeLLMClient:
        async def chat(self, model_type="nl2sql", **kwargs):
            yield """```json
{"relatedFlag": true, "columnIndexes": [2]}
```"""

    module.llm_client = FakeLLMClient()
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


def test_run_error_response_keeps_data_status_for_compat(monkeypatch):
    """异常场景仍使用 status=data，兼容 Java SSE 监听器。"""
    async def raise_rewrite(*args, **kwargs):
        raise RuntimeError("mock rewrite error")

    monkeypatch.setattr(NL2SQLAgent, "_text_to_rewrite", raise_rewrite)

    req = NL2SQLRequest.model_validate(
        {
            "requestId": "req-err-1",
            "query": "测试异常",
            "currentDateInfo": "2026-03-05",
            "modelCodeList": [],
            "schemaInfo": [],
            "stream": False,
            "dbType": "mysql",
        }
    )

    result = asyncio.run(NL2SQLAgent().run(req))
    assert result["code"] == 6001
    assert result["status"] == "data"
    assert "mock rewrite error" in result["err_msg"]
