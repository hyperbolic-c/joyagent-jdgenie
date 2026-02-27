# -*- coding: utf-8 -*-
# =====================
# NL2SQL 请求模型
# =====================
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM 配置模型 - 支持每次请求独立配置"""
    model: Optional[str] = Field(default=None, description="模型名称，如 gpt-4.1")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    base_url: Optional[str] = Field(default=None, description="API 基础 URL")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None)


class NL2SQLRequest(BaseModel):
    """NL2SQL 请求模型 - 保持与现有 genie-tool 接口兼容"""
    request_id: str = Field(alias="requestId", description="请求 ID")
    query: str = Field(description="用户问题")
    current_date_info: str = Field(alias="currentDateInfo", description="系统当前日期")
    table_id_list: List[str] = Field(alias="modelCodeList", default=[], description="表信息")
    column_info: List[Dict] = Field(alias="schemaInfo", default=[], description="字段信息")
    stream: bool = Field(default=True, description="是否流式响应")
    dialect: str = Field(alias="dbType", default="mysql", description="SQL 方言类型")

    # 可选的 LLM 配置（如不提供则使用环境变量，保持向后兼容）
    llm_config: Optional[LLMConfig] = Field(alias="llmConfig", default=None)
