# -*- coding: utf-8 -*-
# =====================
#
#
# Author: liumin.423
# Date:   2025/7/8
# =====================
import contextvars


class _RequestIdCtx(object):
    def __init__(self):
        self._request_id = contextvars.ContextVar("request_id", default="default-request-id")

    @property
    def request_id(self):
        return self._request_id.get()

    @request_id.setter
    def request_id(self, value):
        self._request_id.set(value)


RequestIdCtx = _RequestIdCtx()
