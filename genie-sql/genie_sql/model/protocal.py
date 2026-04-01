# -*- coding: utf-8 -*-
# =====================
#
#
# Author: liumin.423
# Date:   2025/7/7
# =====================
from typing import Dict, List

from pydantic import BaseModel, Field


class NL2SQLRequest(BaseModel):
    request_id: str = Field(alias="requestId", description="Request ID")
    query: str = Field(description="用户问题")
    current_date_info: str = Field(alias="currentDateInfo", description="系统当前日期")
    table_id_list: List[str] = Field(alias="modelCodeList", description="表信息")
    column_info: List[Dict] = Field(alias="schemaInfo", description="字段信息")
    stream: bool = Field(alias="stream", default=True, description="是否流式响应")
    dialect: str = Field(alias="dbType", default="mysql", description="SQL方言类型")
