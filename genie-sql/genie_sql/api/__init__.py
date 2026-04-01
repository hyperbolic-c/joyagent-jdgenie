# -*- coding: utf-8 -*-
# =====================
#
#
# Author: liumin.423
# Date:   2025/7/7
# =====================
from fastapi import APIRouter

from .tool import router as tool_router

api_router = APIRouter(prefix="/v1")

api_router.include_router(tool_router, prefix="/tool", tags=["tool"])
