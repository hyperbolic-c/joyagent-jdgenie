# -*- coding: utf-8 -*-
# =====================
#
#
# Author: liumin.423
# Date:   2025/7/7
# =====================
import asyncio
import contextvars
import json
import threading

from dotenv import load_dotenv
from fastapi import APIRouter
from sse_starlette import EventSourceResponse, ServerSentEvent

from genie_sql.model.protocal import NL2SQLRequest
from genie_sql.tool.nl2sql import NL2SQLAgent
from genie_sql.util.middleware_util import RequestHandlerRoute

load_dotenv()


router = APIRouter(route_class=RequestHandlerRoute)


@router.post("/nl2sql")
async def post_nl2sql(body: NL2SQLRequest):
    """
    text_2_sql
    """
    nl2sql_queue = asyncio.Queue()
    if body.stream:
        async def _stream(queue):
            if not body.query:
                yield ServerSentEvent(data="没有提供用户问题，无法进行nl2sql的执行")
            else:
                while True:
                    data = await queue.get()
                    if data == "[DONE]":
                        yield ServerSentEvent(data=data)
                        break
                    if not isinstance(data, str):
                        data = json.dumps(data, ensure_ascii=False)
                    yield ServerSentEvent(data=data)

        def run_task(context, queue, body: NL2SQLRequest):
            if body.query:
                context.run(lambda: asyncio.run(NL2SQLAgent(queue=queue).run(body)))

        thread = threading.Thread(target=run_task, args=(contextvars.copy_context(), nl2sql_queue, body), daemon=True)
        thread.start()
        return EventSourceResponse(
            _stream(nl2sql_queue),
            ping_message_factory=lambda: ServerSentEvent(data="heartbeat"),
            ping=15,
        )

    response = {"code": 200, "data": {}, "request_id": body.request_id, "status": "data"}
    if not body.query:
        response["err_msg"] = "没有提供用户问题，无法进行nl2sql的执行"
    else:
        response = await NL2SQLAgent().run(body)
    return response
