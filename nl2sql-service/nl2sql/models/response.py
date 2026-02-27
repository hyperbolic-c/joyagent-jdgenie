# -*- coding: utf-8 -*-
# =====================
# NL2SQL 响应模型
# =====================
from typing import List, Optional

from pydantic import BaseModel, Field


class NL2SQLData(BaseModel):
    """单条 SQL 结果"""
    query: str = Field(description="子问题")
    nl2sql: str = Field(description="生成的 SQL")


class NL2SQLResponse(BaseModel):
    """NL2SQL 响应模型 - 与现有 genie-tool 格式完全一致"""
    code: int = Field(description="状态码: 200 成功, 其他失败")
    request_id: str = Field(alias="requestId", description="请求 ID")
    status: str = Field(description="状态: nl2sql_think/ finished_stream/ data/ finished/ error")
    nl2sql_think: Optional[str] = Field(alias="nl2sqlThink", default=None, description="思考过程")
    data: List[NL2SQLData] = Field(default=[], description="SQL 结果列表")
    err_msg: Optional[str] = Field(alias="errMsg", default=None, description="错误信息")
