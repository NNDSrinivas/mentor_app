import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Set

import websockets

log = logging.getLogger(__name__)


class IDEBridge:
    """WebSocket bridge between the backend and arbitrary IDE clients."""

    def __init__(self) -> None:
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self._pending: Dict[str, asyncio.Future] = {}

    async def handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Handle incoming messages from an IDE client."""
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type == "confirmation":
                    # Client responded to a confirmation request
                    confirm_id = data.get("id")
                    future = self._pending.get(confirm_id)
                    if future and not future.done():
                        future.set_result(bool(data.get("approved")))
                else:
                    # Process other events concurrently so we don't block
                    asyncio.create_task(self.process_event(data))
        finally:
            self.clients.discard(websocket)

    async def process_event(self, data: Dict[str, Any]) -> None:
        """Process a generic event from the IDE."""
        if data.get("requires_confirmation"):
            prompt = data.get("prompt", "Are you sure?")
            # Previously this used input(); now it sends a prompt to the client
            approved = await self.request_confirmation(prompt)
            if approved:
                log.info("Action confirmed: %s", data.get("action"))
            else:
                log.info("Action rejected: %s", data.get("action"))
        else:
            log.info("Processing event: %s", data)

    async def request_confirmation(self, prompt: str) -> bool:
        """Ask the connected client to confirm an action and await the reply."""
        if not self.clients:
            log.warning("No IDE clients connected; denying action: %s", prompt)
            return False

        confirm_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[confirm_id] = future

        payload = json.dumps({"type": "confirm", "id": confirm_id, "prompt": prompt})
        await asyncio.gather(*(client.send(payload) for client in self.clients))

        # Await the client's response while other events continue to be handled
        return await future

    async def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """Start the bridge server and run indefinitely."""
        async with websockets.serve(self.handler, host, port):
            log.info("Universal IDE Bridge running on %s:%d", host, port)
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = IDEBridge()
    asyncio.run(bridge.start())
