# -*- coding: utf-8 -*-
"""
NL2SQL 数据模型
"""
from .request import LLMConfig, NL2SQLRequest
from .response import NL2SQLData, NL2SQLResponse

__all__ = [
    "LLMConfig",
    "NL2SQLRequest",
    "NL2SQLData",
    "NL2SQLResponse",
]
