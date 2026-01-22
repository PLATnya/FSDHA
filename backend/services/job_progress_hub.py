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
            count = len(self._subscribers.get(job_id, set()))
            logger.debug(f"WebSocket subscribed to job {job_id}, total subscribers: {count}")

    async def unsubscribe(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            subs = self._subscribers.get(job_id)
            if not subs:
                logger.debug(f"Attempted to unsubscribe from job {job_id} with no subscribers")
                return
            subs.discard(websocket)
            remaining = len(subs)
            if not subs:
                self._subscribers.pop(job_id, None)
                logger.debug(f"WebSocket unsubscribed from job {job_id}, no remaining subscribers")
            else:
                logger.debug(f"WebSocket unsubscribed from job {job_id}, remaining subscribers: {remaining}")

    async def subscriber_count(self, job_id: str) -> int:
        async with self._lock:
            return len(self._subscribers.get(job_id, set()))

    async def publish(self, job_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            recipients: List[WebSocket] = list(self._subscribers.get(job_id, set()))

        if not recipients:
            logger.debug(f"No subscribers for job {job_id}, skipping publish")
            return

        logger.debug(f"Publishing to {len(recipients)} subscribers for job {job_id}, type: {payload.get('type', 'unknown')}")
        dead: List[WebSocket] = []
        for ws in recipients:
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"WebSocket send failed for job {job_id}: {e}")
                dead.append(ws)

        if dead:
            logger.debug(f"Removing {len(dead)} dead WebSocket connections for job {job_id}")
            async with self._lock:
                subs = self._subscribers.get(job_id)
                if subs:
                    for ws in dead:
                        subs.discard(ws)
                    if not subs:
                        self._subscribers.pop(job_id, None)
                        logger.debug(f"No remaining subscribers for job {job_id}, removed from hub")


job_progress_hub = JobProgressHub()

