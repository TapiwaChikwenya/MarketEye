"""
Server-Sent Events (SSE) alert stream.

The Celery worker publishes triggered alert payloads to the Redis channel
``alert_notifications``.  The SSE endpoint subscribes to that channel and
relays events to each connected browser, filtered by ``user_id``.

This keeps the Celery worker and the FastAPI process fully decoupled -- they
only share a Redis pub/sub channel.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL_NAME = "alert_notifications"

_redis_pool: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    return _redis_pool


async def publish_alert(payload: dict) -> None:
    """Publish a triggered alert to Redis pub/sub (called from Celery)."""
    r = _get_redis()
    await r.publish(CHANNEL_NAME, json.dumps(payload))


def publish_alert_sync(payload: dict) -> None:
    """Synchronous wrapper for use inside Celery tasks."""
    import redis as sync_redis

    r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.publish(CHANNEL_NAME, json.dumps(payload))
    r.close()


async def subscribe_alerts(user_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings for alerts belonging to *user_id*.

    Sends a heartbeat comment every 15 s so proxies / browsers don't
    time out the connection.
    """
    r = _get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL_NAME)

    try:
        while True:
            msg = await asyncio.wait_for(
                pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                timeout=15.0,
            )
            if msg and msg["type"] == "message":
                try:
                    data = json.loads(msg["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                if data.get("user_id") == user_id:
                    yield f"data: {json.dumps(data)}\n\n"
            else:
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL_NAME)
        await pubsub.close()
