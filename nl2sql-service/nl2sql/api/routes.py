# -*- coding: utf-8 -*-
# =====================
# API 路由
# =====================
import asyncio
import contextvars
import json
import threading

from fastapi import APIRouter
from sse_starlette import EventSourceResponse, ServerSentEvent

from nl2sql.core import NL2SQLAgent
from nl2sql.models import NL2SQLRequest, NL2SQLResponse
from nl2sql.utils import get_logger

logger = get_logger("nl2sql.api")

router = APIRouter()


@router.post("/nl2sql")
async def post_nl2sql(body: NL2SQLRequest):
    """
    NL2SQL 接口 - 与 genie-tool 完全兼容

    接口路径: /v1/tool/nl2sql
    请求/响应格式与现有 genie-tool 保持一致
    """
    nl2sql_queue = asyncio.Queue()

    if body.stream:
        # 流式响应
        async def _stream(queue):
            if not body.query:
                yield ServerSentEvent(data="没有提供用户问题，无法进行nl2sql的执行")
                return

            while True:
                data = await queue.get()
                if data == "[DONE]":
                    yield ServerSentEvent(data=data)
                    break
                if not isinstance(data, str):
                    data = json.dumps(data, ensure_ascii=False)
                yield ServerSentEvent(data=data)

        def run_task(context, queue, request: NL2SQLRequest):
            if request.query:
                context.run(lambda: asyncio.run(
                    NL2SQLAgent(
                        queue=queue,
                        llm_config=request.llm_config
                    ).run(request)
                ))

        thread = threading.Thread(
            target=run_task,
            args=(contextvars.copy_context(), nl2sql_queue, body),
            daemon=True
        )
        thread.start()

        return EventSourceResponse(
            _stream(nl2sql_queue),
            ping_message_factory=lambda: ServerSentEvent(data="heartbeat"),
            ping=15,
        )

    else:
        # 非流式响应
        response = {"code": 200, "data": {}, "request_id": body.request_id, "status": "data"}
        if not body.query:
            response["err_msg"] = "没有提供用户问题，无法进行nl2sql的执行"
        else:
            result = await NL2SQLAgent(llm_config=body.llm_config).run(body)
            response = result
        return response


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "nl2sql-service"}
