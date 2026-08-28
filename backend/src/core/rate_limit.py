"""
Minimal in-memory rate limiter.

For a single-process deployment this is enough to blunt brute-force login
attempts and chat-endpoint abuse. For a multi-worker/multi-instance
deployment, replace the in-memory dict with Redis (INCR + EXPIRE), which is
a drop-in swap given the interface below.
"""

import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.core.settings import settings

# path_prefix -> {client_key: deque[timestamps]}
_hits: dict[str, dict[str, deque]] = defaultdict(lambda: defaultdict(deque))

RATE_LIMITED_PREFIXES = ("/auth/login", "/auth/token", "/auth/register", "/chat")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        matched_prefix = next(
            (p for p in RATE_LIMITED_PREFIXES if path.startswith(p)), None
        )

        if matched_prefix is None:
            return await call_next(request)

        client_key = request.client.host if request.client else "unknown"
        window_seconds = 60
        limit = settings.RATE_LIMIT_PER_MINUTE

        now = time.time()
        bucket = _hits[matched_prefix][client_key]

        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again shortly."
                },
            )

        bucket.append(now)

        return await call_next(request)
