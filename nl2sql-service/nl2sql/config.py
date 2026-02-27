# -*- coding: utf-8 -*-
# =====================
# 服务配置
# =====================
import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """服务配置"""
    # 服务配置
    port: int = Field(default=1601, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_path: str = Field(default="logs/nl2sql.log", alias="LOG_PATH")

    # LLM 默认配置
    default_llm_model: str = Field(default="gpt-4.1", alias="DEFAULT_LLM_MODEL")
    default_llm_api_key: Optional[str] = Field(default=None, alias="DEFAULT_LLM_API_KEY")
    default_llm_base_url: str = Field(default="https://api.openai.com/v1", alias="DEFAULT_LLM_BASE_URL")

    # NL2SQL 专用模型配置（向后兼容）
    nl2sql_model_name: str = Field(default="gpt-4.1", alias="NL2SQL_MODEL_NAME")
    rewrite_model_name: str = Field(default="gpt-4.1", alias="REWRITE_MODEL_NAME")
    think_model_name: str = Field(default="gpt-4.1", alias="THINK_MODEL_NAME")
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
