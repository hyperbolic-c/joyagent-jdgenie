# -*- coding: utf-8 -*-
# =====================
# LLM 调用客户端
# =====================
import json
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from litellm import acompletion

from nl2sql.models import LLMConfig


class LLMClient:
    """LLM 调用客户端 - 支持请求级配置覆盖环境变量"""

    def __init__(self, request_config: Optional[LLMConfig] = None):
        """
        Args:
            request_config: 请求级 LLM 配置，优先于环境变量
        """
        self.request_config = request_config

    def _get_config(self, model_type: str = "nl2sql") -> Dict:
        """
        获取最终配置：请求配置 > 环境变量 > 默认值

        Args:
            model_type: 模型类型 (nl2sql/rewrite/think)
        """
        # 环境变量映射
        env_var_map = {
            "nl2sql": "NL2SQL_MODEL_NAME",
            "rewrite": "REWRITE_MODEL_NAME",
            "think": "THINK_MODEL_NAME",
            # 保持与原版字段精排模块的环境变量命名兼容
            "column_filter": "TR_TABLE_FILTER_MODEL_NAME",
            "table_filter": "TR_COLUMN_FILTER_MODEL_NAME",
        }

        default_model = "gpt-4.1"

        config = {
            "model": os.getenv(env_var_map.get(model_type, "NL2SQL_MODEL_NAME"), default_model),
            "api_key": os.getenv("LLM_API_KEY"),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            "temperature": 0.0,
            "top_p": 0.0,
        }

        # 请求级配置覆盖环境变量
        if self.request_config:
            if self.request_config.model:
                config["model"] = self.request_config.model
            if self.request_config.api_key:
                config["api_key"] = self.request_config.api_key
            if self.request_config.base_url:
                config["base_url"] = self.request_config.base_url
            config["temperature"] = self.request_config.temperature
            config["top_p"] = self.request_config.top_p

        return config

    async def chat(
        self,
        messages: Union[str, List[Dict]],
        model_type: str = "nl2sql",
        stream: bool = False,
        only_content: bool = True,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> AsyncGenerator[Union[str, Any], None]:
        """
        调用 LLM

        Args:
            messages: 消息内容
            model_type: 模型类型 (nl2sql/rewrite/think)
            stream: 是否流式
            only_content: 是否只返回内容
            extra_headers: 额外请求头

        Yields:
            流式模式下返回 chunk，非流式模式下返回完整内容
        """
        config = self._get_config(model_type)
        if model:
            config["model"] = model
        if temperature is not None:
            config["temperature"] = temperature
        if top_p is not None:
            config["top_p"] = top_p

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        response = await acompletion(
            messages=messages,
            model=config["model"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=config["temperature"],
            top_p=config["top_p"],
            stream=stream,
            extra_headers=extra_headers,
        )

        if stream:
            async for chunk in response:
                if only_content:
                    if (
                        chunk.choices
                        and chunk.choices[0]
                        and chunk.choices[0].delta
                        and chunk.choices[0].delta.content
                    ):
                        yield chunk.choices[0].delta.content
                else:
                    yield chunk
        else:
            yield response.choices[0].message.content if only_content else response
