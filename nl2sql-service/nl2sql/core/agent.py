# -*- coding: utf-8 -*-
# =====================
# NL2SQL 核心算法
# =====================
import asyncio
import json
import os
from typing import Dict, List, Optional

import yaml
from jinja2 import Template

from nl2sql.llm import LLMClient
from nl2sql.models import LLMConfig, NL2SQLRequest, NL2SQLData
from nl2sql.utils import get_logger, timer

logger = get_logger("nl2sql.agent")


class NL2SQLAgent:
    """NL2SQL 核心代理类"""

    def __init__(
        self,
        queue: Optional[asyncio.Queue] = None,
        llm_config: Optional[LLMConfig] = None
    ):
        """
        Args:
            queue: 用于流式输出的队列
            llm_config: 请求级 LLM 配置（优先于环境变量）
        """
        self.queue = queue or asyncio.Queue()
        self.llm_config = llm_config
        self.llm_client = LLMClient(request_config=llm_config)
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> Dict:
        """加载 Prompt 模板"""
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "nl2sql.yaml"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @timer(key="rewrite_query")
    async def _text_to_rewrite(
        self,
        request_id: str,
        query: str,
    ) -> str:
        """
        重写用户查询（非流式）
        将用户的原始查询优化为更清晰、更适合后续处理的表达方式
        """
        prompt_template = Template(self._prompts["rewrite_prompt"])
        prompt = prompt_template.render(
            query=query,
            business_info="",
            user_info="",
            time_info=""
        )
        logger.info(f"[NL2SQL] [REWRITE] request_id={request_id} prompt={prompt[:200]}...")

        rewrite_result = ""
        async for chunk in self.llm_client.chat(
            messages=prompt,
            model_type="rewrite",
            stream=False,
            only_content=True
        ):
            rewrite_result = chunk

        logger.info(f"[NL2SQL] [REWRITE] request_id={request_id} result={rewrite_result[:200]}...")
        return rewrite_result

    @timer(key="think")
    async def _collect_think_results(
        self,
        request_id: str,
        query: str,
        current_date_info: str,
        m_schema_formatted: str,
    ) -> str:
        """收集 think 的完整结果（流式输出）"""
        response = {
            "code": 200,
            "err_msg": "",
            "status": "",
            "nl2sql_think": "",
            "data": [],
            "request_id": request_id
        }

        think_full = ""
        prompt_template = Template(self._prompts["think_prompt"])
        prompt = prompt_template.render(
            query=query,
            column_info="",
            m_schema_formatted=m_schema_formatted,
            current_date_info=current_date_info,
            user_info=""
        )
        logger.info(f"[NL2SQL] [THINK] request_id={request_id} prompt={prompt[:200]}...")

        async for chunk in self.llm_client.chat(
            messages=prompt,
            model_type="think",
            stream=True,
            only_content=False
        ):
            chunk_content = chunk.choices[0].delta.content
            if chunk_content is None or chunk_content == "":
                continue
            think_full += chunk_content
            response["nl2sql_think"] = think_full
            response["status"] = "nl2sql_think"
            await self.queue.put(json.dumps(response, ensure_ascii=False))

        # 思考模型结束标识
        final_response = {
            "code": 200,
            "err_msg": "",
            "status": "finished_stream",
            "nl2sql_think": "",
            "data": [],
            "request_id": request_id
        }
        await self.queue.put(json.dumps(final_response, ensure_ascii=False))
        logger.info(f"[NL2SQL] [THINK] request_id={request_id} completed")

        return think_full

    def _m_schema_trans(
        self,
        table_id: str,
        column_schema_lists: List[Dict],
        business_prompt: str = "",
        time_prompt: str = "",
        use_prompt: str = "",
    ) -> str:
        """格式化单张表的字段信息"""
        output = [f"\n## 数据表：{table_id}\n如果要使用当前的数据表，只能使用以下的字段，禁止使用其他数据表的字段。该表字段信息的详细描述："]
        field_lines = []

        for column_schema_info in column_schema_lists:
            field_line = []
            field_type = column_schema_info.get("dataType", "")
            raw_type = field_type
            field_id = column_schema_info.get("columnId", "")
            field_name = column_schema_info.get("columnName", "")
            field_comment = column_schema_info.get("columnComment", "")
            alias_name = column_schema_info.get("synonyms", "")
            few_shot = column_schema_info.get("fewShot", "")

            if field_id and field_id.strip():
                field_line.append(f"字段ID：{field_id}")
            if field_name and field_name.strip():
                field_line.append(f"- 字段名称：{field_name}")
            if raw_type and raw_type.strip():
                field_line.append(f"- 字段类型：{raw_type}")
            if field_comment and field_comment.strip():
                field_line.append(f"- 字段描述：{field_comment}")
            if alias_name and alias_name.strip():
                field_line.append(f"- 字段别名：{alias_name}")
            if few_shot and few_shot.strip():
                field_line.append(f"- 字段举例：{few_shot}")

            field_lines.append("\n".join(field_line))

        output.append("\n\n".join(field_lines))

        if business_prompt and len(business_prompt) > 0:
            output.append(f"### 业务规则：\n{business_prompt}")
        if time_prompt and len(time_prompt) > 0:
            output.append(f"### 时间规则：\n{time_prompt}")
        if use_prompt and len(use_prompt) > 0:
            output.append(f"### 数据表使用规范：\n{use_prompt}")

        return "\n".join(output)

    async def _m_schema_format(self, column_info: List[Dict]) -> str:
        """格式化所有表结构信息"""
        m_schema_results = []

        for table_schema_info in column_info:
            table_id = table_schema_info.get("modelCode", "")
            schema_list = table_schema_info.get("schemaList", [])
            business_prompt = table_schema_info.get("businessPrompt", "")
            time_prompt = table_schema_info.get("timePrompt", "")
            use_prompt = table_schema_info.get("usePrompt", "")

            if table_id and schema_list:
                formatted = self._m_schema_trans(
                    table_id=table_id,
                    column_schema_lists=schema_list,
                    business_prompt=business_prompt,
                    time_prompt=time_prompt,
                    use_prompt=use_prompt
                )
                m_schema_results.append(formatted)

        return "\n".join(m_schema_results)

    @timer(key="nl2sql_convert")
    async def _nl2sql_convert(
        self,
        request_id: str,
        rewritten_query: str,
        thinking_result: str,
        current_date_info: str,
        m_schema_formatted: str,
        dialect: str
    ) -> Dict:
        """
        将查询转换为 SQL（非流式）
        结合 rewrite 和 think 的结果，生成对应的 SQL 查询
        """
        prompt_template = Template(self._prompts["nl2sql_prompt"])
        prompt = prompt_template.render(
            rewritten_query=rewritten_query,
            thinking_result=thinking_result,
            query=rewritten_query,
            m_schema_formatted=m_schema_formatted,
            current_date_info=current_date_info,
            dialect=dialect,
            user_info=""
        )
        logger.info(f"[NL2SQL] [CONVERT] request_id={request_id} prompt={prompt[:200]}...")

        nl2sql_response = ""
        async for chunk in self.llm_client.chat(
            messages=prompt,
            model_type="nl2sql",
            stream=False,
            only_content=True
        ):
            nl2sql_response = chunk

        logger.info(f"[NL2SQL] [CONVERT] request_id={request_id} response={nl2sql_response[:200]}...")

        # 解析响应
        llm_post_result = []
        if nl2sql_response and nl2sql_response != "{}":
            llm_info_list = nl2sql_response.split("@@@")
            for llm_info in llm_info_list:
                tmp_dict = {}
                query_info_list = llm_info.split("###")
                if len(query_info_list) == 2:
                    tmp_dict["query"] = query_info_list[0]
                    nl2sql = query_info_list[1]
                    nl2sql = nl2sql.replace(";", "")
                    tmp_dict["nl2sql"] = nl2sql
                if tmp_dict:
                    llm_post_result.append(tmp_dict)

        response = {
            "code": 200,
            "data": llm_post_result,
            "request_id": request_id,
            "status": "data",
            "error_msg": ""
        }
        await self.queue.put(json.dumps(response, ensure_ascii=False))

        final_response = {
            "code": 200,
            "err_msg": "",
            "status": "finished",
            "nl2sql_think": "",
            "data": [],
            "request_id": request_id
        }
        await self.queue.put(json.dumps(final_response, ensure_ascii=False))
        logger.info(f"[NL2SQL] request_id={request_id} nl2sql completed")

        return response

    @timer(key="run_nl2sql")
    async def run(self, body: NL2SQLRequest) -> Dict:
        """
        执行完整的 NL2SQL 流程

        流程：
        1. 查询改写 (Rewrite)
        2. 表结构格式化
        3. 思考分析 (Think) - 流式输出
        4. SQL 生成 (NL2SQL)
        """
        request_id = body.request_id
        query = body.query
        current_date_info = body.current_date_info
        column_info = body.column_info
        dialect = body.dialect

        logger.info(f"[NL2SQL] [REQUEST] request_id={request_id} query={query}")

        try:
            # 1. 查询改写
            rewrite_task = asyncio.create_task(
                self._text_to_rewrite(request_id=request_id, query=query)
            )

            # 2. 表结构格式化
            m_schema_formatted = await self._m_schema_format(column_info)

            # 等待改写完成
            rewritten_query = await rewrite_task

            # 3. 思考分析（流式输出）
            full_thinking = await self._collect_think_results(
                request_id=request_id,
                query=query,
                current_date_info=current_date_info,
                m_schema_formatted=m_schema_formatted
            )

            # 4. SQL 生成
            nl2sql_response = await self._nl2sql_convert(
                request_id=request_id,
                rewritten_query=rewritten_query,
                thinking_result=full_thinking,
                current_date_info=current_date_info,
                m_schema_formatted=m_schema_formatted,
                dialect=dialect
            )

            logger.info(f"[NL2SQL] [RESPONSE] request_id={request_id} response={nl2sql_response}")
            return nl2sql_response

        except Exception as e:
            err_response = {
                "code": 6001,
                "data": [],
                "request_id": request_id,
                "err_msg": str(e),
                "status": "error"
            }
            await self.queue.put(json.dumps(err_response, ensure_ascii=False))
            logger.error(f"[NL2SQL] request_id={request_id} error: {e}")
            return err_response

        finally:
            await self.queue.put("[DONE]")
