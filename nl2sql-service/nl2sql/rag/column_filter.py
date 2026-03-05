# -*- coding: utf-8 -*-
"""
字段精排模块（恢复原版两阶段 LLM 过滤逻辑）。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import textwrap
import traceback
from calendar import day_name
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from jinja2 import Template

from nl2sql.llm import LLMClient
from nl2sql.models import LLMConfig
from nl2sql.utils import get_logger

logger = get_logger("nl2sql.column_filter")


def _parse_code_from_string(input_string: str) -> str:
    """从字符串中提取 JSON/代码块内容。"""
    triple_backtick_pattern = r"```(\w*\s*)?(.*?)```"
    match = re.search(triple_backtick_pattern, input_string, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(2).strip()

    single_backtick_pattern = r"`(.*?)`"
    match = re.search(single_backtick_pattern, input_string, flags=re.DOTALL)
    if match:
        return match.group(1).strip()

    return input_string.strip()


def _read_json(text: str):
    return json.loads(_parse_code_from_string(text))


class ColumnFilterModule:
    """对 schemaInfo 进行两阶段过滤（选表 + 字段筛选）。"""

    def __init__(
        self,
        request_id: str,
        query: str,
        current_date_info: str,
        table_id_list: List[str],
        column_info: List[Dict],
        llm_config: Optional[LLMConfig] = None,
    ):
        # 保持与原版实现一致的环境变量命名与行为
        self.llm_model_name = os.getenv("TR_TABLE_FILTER_MODEL_NAME")
        self.table_filter_model_name = os.getenv("TR_COLUMN_FILTER_MODEL_NAME")

        self._is_first_filter_table = os.getenv("TR_IS_FIRST_FILTER_TABLE", True)
        self.need_filter_table_min_length = int(os.getenv("TR_NEED_FILTER_TABLE_MIN_LENGTH", 3))
        self.table_filter_batch_size = int(os.getenv("TR_TABLE_FILTER_BATCH_SIZE", 5))

        self.user_info = ""
        self.memory_info = []
        self.current_date_info = current_date_info
        self.query = query or ""
        self.request_id = request_id
        self.table_schema_lists = table_id_list or []
        self.column_info = column_info or []
        self.schema_list_max_length = int(os.getenv("TR_SCHEMA_LIST_MAX_LENGTH", 200))
        self.business_prompt_max_length = int(os.getenv("TR_BUSINESS_PROMPT_MAX_LENGTH", 3000))
        self.use_prompt_max_length = int(os.getenv("TR_USE_PROMPT_MAX_LENGTH", 500))
        self.llm_client = LLMClient(request_config=llm_config)
        self._prompts = self._load_prompts()

    @staticmethod
    def _load_prompts() -> Dict:
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "table_rag.yaml"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def time_info(self) -> str:
        today = date.today()
        day_of_week = day_name[today.weekday()]
        if self.current_date_info == "" or self.current_date_info == " ":
            self.current_date_info = f"今天是 {today.strftime('%Y年%m月%d日')}，星期{day_of_week}"
        return self.current_date_info

    def schema2str(self, schema) -> str:
        column_name = schema.get("columnName", "") or ""
        few_shot = schema.get("fewShot", "") or ""
        synonyms = schema.get("synonyms", "") or ""
        column_comment = schema.get("columnComment", "") or ""
        schema_str = ""
        if column_name:
            schema_str = "字段名：" + column_name
            if column_comment:
                schema_str += "- 解释：" + column_comment
            if synonyms:
                schema_str += "- 近义词有：" + synonyms
            if few_shot:
                schema_str += "- 取值示例：" + few_shot
        return schema_str

    def schema_list2str(self, schema_list: List[Dict]) -> str:
        schema_list_str = ""
        for schema in schema_list:
            schema_str = self.schema2str(schema)
            schema_list_str += schema_str + "\n"
        return schema_list_str

    def get_memroy_info_str(self):
        memory_info_str = ""
        for message in self.memory_info:
            role = message.get("role", "")
            content = message.get("content", "")
            status = message.get("status", "")
            if content and status:
                memory_info_str += f"{role}: {content}\n"
        return memory_info_str

    def _generate_table_filter_prompt(self, table_schema_info_list, error_msg: str | None):
        table_info_list_str = ""
        index2model_code_id_map = {}
        for index, table_schema_info in enumerate(table_schema_info_list):
            table_id = index + 1
            table_name = table_schema_info.get("modelName", "")
            schema_list = table_schema_info.get("schemaList", [])
            schema_list_str = self.schema_list2str(schema_list)[: self.schema_list_max_length]
            business_prompt = table_schema_info.get("businessPrompt", "")[: self.business_prompt_max_length]
            use_prompt = table_schema_info.get("usePrompt", "")[: self.use_prompt_max_length]

            table_info_str = f"""
                                <编号>：{table_id} <编号>
                                <表名>：{table_name}<表名>
                                <表描述>：{business_prompt}<表描述>
                                <使用说明>：{use_prompt}<使用说明>
                                <表的相关字段>：{schema_list_str}<表的相关字段>
                                """
            table_info_list_str += textwrap.dedent(table_info_str) + "\n\n"
            index2model_code_id_map[table_id] = table_schema_info

        memory_info_str = self.get_memroy_info_str()
        model_code_list = [index + 1 for index in range(len(table_schema_info_list))]
        table_info = table_info_list_str.strip()

        prompt = Template(self._prompts["table_filter_prompt"]).render(
            model_code_list=model_code_list,
            table_info=table_info,
            user_info=self.user_info,
            time_info=self.time_info,
            query=self.query,
            memory_info=memory_info_str,
            error_msg=error_msg or "",
        )

        return prompt, index2model_code_id_map

    def _generate_filter_prompt(self, table_schema_info: dict, error_msg: str | None):
        table_name = table_schema_info.get("modelName", "")
        columns = table_schema_info.get("schemaList", [])

        to_model_columns = []
        keep_keys = ["columnIndex", "columnName", "columnComment", "synonyms", "fewShot", "dataType"]
        for i in range(len(columns)):
            column = columns[i]
            column["columnIndex"] = i + 1
            to_model_column = {}
            for key in keep_keys:
                if key in column:
                    to_model_column[key] = column[key]
            to_model_columns.append(to_model_column)

        memory_info_str = self.get_memroy_info_str()
        table_info = {
            "tableName": table_name,
            "businessPrompt": table_schema_info.get("businessPrompt", ""),
            "usePrompt": table_schema_info.get("usePrompt", ""),
            "columns": to_model_columns,
        }

        info_dict = {
            "table_info": table_info,
            "user_info": self.user_info,
            "time_info": self.time_info,
            "query": self.query,
            "memory_info": memory_info_str,
            "error_msg": error_msg or "",
        }
        prompt = Template(self._prompts["column_filter_prompt"]).render(info_dict)
        return prompt

    def _parse_json_result(self, result_str):
        pattern = r"```json\s*([\s\S]*?)\s*```"
        try:
            result = re.findall(pattern, result_str)
            return result[0]
        except Exception as e:
            logger.error(f"生成结果格式不合法: {result_str}，{e}")
            raise RuntimeError("解析llm json结果失败")

    async def _filter_single_table(self, semaphore, table_schema_info: dict) -> dict | None:
        async with semaphore:
            llm_response = ""
            request_id = ""
            error_msg = None
            for retry in range(3):
                try:
                    columns_prompt = self._generate_filter_prompt(table_schema_info, error_msg)
                    messages = [
                        {"role": "system", "content": "you are a helpful assistant."},
                        {"role": "user", "content": columns_prompt},
                    ]
                    request_id = self.request_id

                    async for chunk in self.llm_client.chat(
                        messages=messages,
                        model_type="column_filter",
                        stream=False,
                        temperature=0,
                        top_p=0.95,
                        only_content=True,
                        model=self.llm_model_name,
                    ):
                        llm_response += chunk

                    result_dict = json.loads(self._parse_json_result(llm_response))
                    if str(result_dict.get("relatedFlag")).lower() == "true":
                        columns = table_schema_info.get("schemaList", [])
                        filter_columns = []
                        result_column_indexes = result_dict.get("columnIndexes", [])
                        for column_info in columns:
                            column_index = column_info.get("columnIndex", "")
                            default_recall = column_info.get("defaultRecall", 0)
                            if column_index in result_column_indexes or default_recall == 1:
                                filter_columns.append(column_info)
                        table_schema_info["schemaList"] = filter_columns
                        return table_schema_info
                    return None
                except Exception as e:
                    error_msg = f"第{retry + 1}次执行结果:\n{llm_response}，报错信息:{e}"
                    traceback.print_exc()
                    logger.error(f"[filter column] {request_id}, fail to filter columns error_msg {error_msg}")
                    continue

            raise RuntimeError(f"[filter column] {request_id} 多次重试后执行失败, error_msg:{error_msg}")

    async def batch_get_stage_result(self):
        table_schema_lists = self.column_info
        if not table_schema_lists:
            return []

        batch_size = self.table_filter_batch_size
        semaphore1 = asyncio.Semaphore(self.table_filter_batch_size)

        def batch_generator():
            for i in range(0, len(table_schema_lists), batch_size):
                yield table_schema_lists[i : i + batch_size]

        batch_tasks = [
            asyncio.create_task(self.filter_table(semaphore1, batch))
            for batch in batch_generator()
        ]

        second_stage_tasks = []
        semaphore2 = asyncio.Semaphore(self.table_filter_batch_size)

        for coro in asyncio.as_completed(batch_tasks):
            try:
                filtered_batch = await coro
                if not filtered_batch:
                    continue
                for item in filtered_batch:
                    task = asyncio.create_task(self._filter_single_table(semaphore2, item))
                    second_stage_tasks.append(task)
            except Exception as e:
                err_msg = traceback.format_exc().replace("\n", "\\n")
                logger.error(f"Error in first stage batch: {e} error_msg {err_msg}")
                continue

        if not second_stage_tasks:
            return []

        filter_tables = await asyncio.gather(*second_stage_tasks, return_exceptions=True)
        return [r for r in filter_tables if not isinstance(r, Exception)]

    async def filter_table(self, semaphore, schema_info_list):
        async with semaphore:
            if schema_info_list is None or len(schema_info_list) == 0:
                return []

            request_id = self.request_id
            model_code_list = [table_schema_info.get("modelCode", "") for table_schema_info in schema_info_list]
            logger.info(f"sn: {request_id} Start [filter tables] tables: {model_code_list}")

            prompt, index2model_code_map = self._generate_table_filter_prompt(schema_info_list, None)
            messages = [
                {"role": "system", "content": "you are a helpful assistant"},
                {"role": "user", "content": prompt},
            ]

            llm_response = ""
            async for chunk in self.llm_client.chat(
                messages=messages,
                model_type="table_filter",
                stream=False,
                temperature=0,
                top_p=0.95,
                only_content=True,
                model=self.table_filter_model_name,
            ):
                llm_response += chunk

            logger.info(f"llm_response = {llm_response}")
            llm_response = llm_response[llm_response.find("[") : llm_response.find("]") + 1]
            model_code_index_list = _read_json(llm_response)
            schema_info_list = [index2model_code_map[index] for index in model_code_index_list]
            return schema_info_list

    async def batch_get_result(self):
        table_schema_lists = self.column_info
        if len(table_schema_lists) < self.need_filter_table_min_length or not self._is_first_filter_table:
            semaphore = asyncio.Semaphore(self.table_filter_batch_size)
            filter_tables = await asyncio.gather(
                *[self._filter_single_table(semaphore, item) for item in table_schema_lists]
            )
        else:
            filter_tables = await self.batch_get_stage_result()

        filter_tables = [table for table in filter_tables if table]
        return filter_tables
