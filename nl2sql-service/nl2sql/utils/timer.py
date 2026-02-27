# -*- coding: utf-8 -*-
# =====================
# 性能计时装饰器
# =====================
import functools
import time
from typing import Callable

from .logging import get_logger

logger = get_logger("timer")


def timer(key: str = None):
    """计时装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                logger.debug(f"[TIMER] {key or func.__name__}: {elapsed:.3f}s")

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                logger.debug(f"[TIMER] {key or func.__name__}: {elapsed:.3f}s")

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


import asyncio
