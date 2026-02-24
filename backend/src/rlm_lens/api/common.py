from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import Request
from fastapi.responses import StreamingResponse

from ..services import Services


def get_services(request: Request) -> Services:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("Services not initialized")
    return cast(Services, services)


def sse_response(events: AsyncIterator[dict[str, Any]]) -> StreamingResponse:
    async def gen() -> AsyncIterator[str]:
        async for event in events:
            data = json.dumps(event)
            yield f"data: {data}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
