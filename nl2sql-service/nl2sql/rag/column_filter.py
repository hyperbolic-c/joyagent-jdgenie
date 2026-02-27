# -*- coding: utf-8 -*-
"""
轻量字段精排模块。
"""
from __future__ import annotations

import re
from typing import Dict, List


class ColumnFilterModule:
    """对 schemaInfo 进行表级和字段级筛选。"""

    def __init__(
        self,
        request_id: str,
        query: str,
        current_date_info: str,
        table_id_list: List[str],
        column_info: List[Dict],
    ):
        self.request_id = request_id
        self.query = query or ""
        self.current_date_info = current_date_info
        self.table_id_list = table_id_list or []
        self.column_info = column_info or []

    @staticmethod
    def _split_keywords(text: str) -> List[str]:
        tokens = re.split(r"[\s,，。！？、:：;；()（）\[\]{}]+", text)
        return [token.strip().lower() for token in tokens if token and len(token.strip()) >= 2]

    def _column_score(self, query_keywords: List[str], column: Dict) -> int:
        searchable = " ".join(
            [
                str(column.get("columnId", "")),
                str(column.get("columnName", "")),
                str(column.get("columnComment", "")),
                str(column.get("synonyms", "")),
                str(column.get("fewShot", "")),
            ]
        ).lower()

        if not searchable.strip():
            return 0

        score = 0
        for keyword in query_keywords:
            if keyword in searchable:
                score += 1

        if column.get("defaultRecall", 0) == 1:
            score += 1
        return score

    async def batch_get_result(self) -> List[Dict]:
        """
        返回经过筛选的 schemaInfo。
        - 先按 modelCodeList 做表筛选
        - 再按 query 关键词做字段筛选
        """
        if not self.column_info:
            return []

        filtered_tables: List[Dict] = []
        allow_tables = set(self.table_id_list)

        for table in self.column_info:
            table_id = str(table.get("modelCode", ""))
            if allow_tables and table_id not in allow_tables:
                continue
            filtered_tables.append(table)

        if not filtered_tables:
            filtered_tables = self.column_info

        query_keywords = self._split_keywords(self.query)
        if not query_keywords:
            return filtered_tables

        result: List[Dict] = []
        for table in filtered_tables:
            schema_list = table.get("schemaList", [])
            if not schema_list:
                continue

            scored_columns = [
                (self._column_score(query_keywords, column), column)
                for column in schema_list
            ]
            matched_columns = [column for score, column in scored_columns if score > 0]
            # 保底不降级：若无命中，保留原表全部字段
            table_copy = dict(table)
            table_copy["schemaList"] = matched_columns or schema_list
            result.append(table_copy)

        return result
