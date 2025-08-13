import asyncio
import logging
from typing import Optional

import websockets
from websockets.exceptions import WebSocketException

log = logging.getLogger(__name__)


class IDEBridge:
    """Simple WebSocket client with retry logic for IDE integrations."""

    def __init__(self, url: str, retry_delay: float = 5.0) -> None:
        self.url = url
        self.retry_delay = retry_delay
        self._task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Continuously attempt to connect and listen for messages."""
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    log.info("IDEBridge connected to %s", self.url)
                    await self._listen(ws)
            except (WebSocketException, OSError) as e:
                log.error("IDEBridge connection error: %s", e)
            except Exception as e:  # pragma: no cover - unexpected
                log.error("IDEBridge unexpected error: %s", e)
            log.info("IDEBridge retrying in %s seconds", self.retry_delay)
            await asyncio.sleep(self.retry_delay)

    async def _listen(self, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            async for message in ws:
                log.debug("IDEBridge received: %s", message)
        except WebSocketException as e:
            log.warning("IDEBridge websocket closed: %s", e)
            raise

    def start(self) -> None:
        if not self._task:
            self._task = asyncio.create_task(self.connect())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
