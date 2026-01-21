import asyncio
import logging
from typing import Dict, Set, Any, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class JobProgressHub:

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, Set[WebSocket]] = {}

    async def subscribe(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.setdefault(job_id, set()).add(websocket)

    async def unsubscribe(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            subs = self._subscribers.get(job_id)
            if not subs:
                return
            subs.discard(websocket)
            if not subs:
                self._subscribers.pop(job_id, None)

    async def subscriber_count(self, job_id: str) -> int:
        async with self._lock:
            return len(self._subscribers.get(job_id, set()))

    async def publish(self, job_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            recipients: List[WebSocket] = list(self._subscribers.get(job_id, set()))

        if not recipients:
            return

        dead: List[WebSocket] = []
        for ws in recipients:
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.debug("WebSocket send failed for job %s: %s", job_id, e)
                dead.append(ws)

        if dead:
            async with self._lock:
                subs = self._subscribers.get(job_id)
                if subs:
                    for ws in dead:
                        subs.discard(ws)
                    if not subs:
                        self._subscribers.pop(job_id, None)


job_progress_hub = JobProgressHub()

