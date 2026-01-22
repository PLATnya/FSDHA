import asyncio
import logging
from typing import Dict, Set, Any, List, Optional
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class JobProgressHub:
    """
    A hub for managing WebSocket subscriptions and broadcasting job progress updates.
    
    This class maintains a registry of WebSocket connections subscribed to specific jobs
    and provides methods to subscribe, unsubscribe, and publish progress updates.
    Thread-safe using asyncio.Lock for concurrent access.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, Set[WebSocket]] = {}

    async def subscribe(self, job_id: str, websocket: WebSocket) -> None:
        """
        Subscribe a WebSocket connection to receive updates for a specific job.
        
        Args:
            job_id: The ID of the job to subscribe to
            websocket: The WebSocket connection to subscribe
        """
        async with self._lock:
            self._subscribers.setdefault(job_id, set()).add(websocket)
            count = len(self._subscribers[job_id])
            logger.debug(
                f"WebSocket subscribed to job {job_id}, total subscribers: {count}",
                extra={"job_id": job_id, "subscriber_count": count}
            )

    async def unsubscribe(self, job_id: str, websocket: WebSocket) -> None:
        """
        Unsubscribe a WebSocket connection from a specific job.
        
        Args:
            job_id: The ID of the job to unsubscribe from
            websocket: The WebSocket connection to unsubscribe
        """
        async with self._lock:
            subs = self._subscribers.get(job_id)
            if not subs:
                logger.debug(
                    f"Attempted to unsubscribe from job {job_id} with no subscribers",
                    extra={"job_id": job_id}
                )
                return
            
            subs.discard(websocket)
            remaining = len(subs)
            
            if not subs:
                self._subscribers.pop(job_id, None)
                logger.debug(
                    f"WebSocket unsubscribed from job {job_id}, no remaining subscribers",
                    extra={"job_id": job_id}
                )
            else:
                logger.debug(
                    f"WebSocket unsubscribed from job {job_id}, remaining subscribers: {remaining}",
                    extra={"job_id": job_id, "remaining_subscribers": remaining}
                )

    async def subscriber_count(self, job_id: str) -> int:
        """
        Get the number of active subscribers for a specific job.
        
        Args:
            job_id: The ID of the job to check
            
        Returns:
            The number of active WebSocket subscribers for the job
        """
        async with self._lock:
            return len(self._subscribers.get(job_id, set()))

    def _remove_dead_connections(self, job_id: str, dead_websockets: List[WebSocket]) -> None:
        """
        Remove dead WebSocket connections from the subscriber registry.
        
        This is a helper method that should be called while holding the lock.
        
        Args:
            job_id: The ID of the job
            dead_websockets: List of WebSocket connections to remove
        """
        if not dead_websockets:
            return
        
        subs = self._subscribers.get(job_id)
        if not subs:
            return
        
        for ws in dead_websockets:
            subs.discard(ws)
        
        if not subs:
            self._subscribers.pop(job_id, None)
            logger.debug(
                f"No remaining subscribers for job {job_id}, removed from hub",
                extra={"job_id": job_id}
            )

    async def publish(self, job_id: str, payload: Dict[str, Any]) -> None:
        """
        Publish a progress update to all subscribers of a specific job.
        
        Dead connections (those that fail to send) are automatically removed
        from the subscriber registry.
        
        Args:
            job_id: The ID of the job to publish updates for
            payload: The message payload to send (must be JSON-serializable)
        """
        # Get a snapshot of recipients while holding the lock
        async with self._lock:
            recipients: List[WebSocket] = list(self._subscribers.get(job_id, set()))

        if not recipients:
            logger.debug(
                f"No subscribers for job {job_id}, skipping publish",
                extra={"job_id": job_id}
            )
            return

        logger.debug(
            f"Publishing to {len(recipients)} subscribers for job {job_id}",
            extra={
                "job_id": job_id,
                "subscriber_count": len(recipients)
            }
        )

        # Send to all recipients without holding the lock (better performance)
        dead: List[WebSocket] = []
        for ws in recipients:
            try:
                await ws.send_json(payload)
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                logger.warning(
                    f"WebSocket send failed for job {job_id}: {e}",
                    extra={"job_id": job_id, "error_type": type(e).__name__}
                )
                dead.append(ws)
            except Exception as e:
                # Log unexpected errors but still mark as dead
                logger.error(
                    f"Unexpected error sending to WebSocket for job {job_id}: {e}",
                    exc_info=True,
                    extra={"job_id": job_id, "error_type": type(e).__name__}
                )
                dead.append(ws)

        # Clean up dead connections while holding the lock
        if dead:
            logger.debug(
                f"Removing {len(dead)} dead WebSocket connections for job {job_id}",
                extra={"job_id": job_id, "dead_count": len(dead)}
            )
            async with self._lock:
                self._remove_dead_connections(job_id, dead)


job_progress_hub = JobProgressHub()

