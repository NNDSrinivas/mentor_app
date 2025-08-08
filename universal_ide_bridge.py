import asyncio
import json
import logging
import pathlib
from typing import Dict, List, Set

import websockets

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class IDEBridge:
    """WebSocket bridge between the AI mentor and IDE extensions."""

    def __init__(self) -> None:
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.tasks: List[str] = []

    async def register(self, websocket: websockets.WebSocketServerProtocol) -> None:
        self.clients.add(websocket)
        logging.info("Client connected: %s", websocket.remote_address)

    async def unregister(self, websocket: websockets.WebSocketServerProtocol) -> None:
        self.clients.discard(websocket)
        logging.info("Client disconnected: %s", websocket.remote_address)

    async def broadcast_tasks(self) -> None:
        if not self.clients:
            return
        message = json.dumps({"type": "tasks", "tasks": self.tasks})
        await asyncio.gather(*(client.send(message) for client in self.clients))

    async def handle_patch(self, data: Dict[str, str], websocket: websockets.WebSocketServerProtocol) -> None:
        file_path = data.get("file")
        content = data.get("content", "")
        if not file_path:
            await websocket.send(json.dumps({"type": "error", "message": "Missing file path"}))
            return

        try:
            confirm = input(f"Apply patch to {file_path}? [y/N]: ").strip().lower()
        except EOFError:
            confirm = "n"

        if confirm != "y":
            await websocket.send(json.dumps({"type": "patch_rejected", "file": file_path}))
            return

        path = pathlib.Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        logging.info("Applied patch to %s", file_path)
        await websocket.send(json.dumps({"type": "patch_applied", "file": file_path}))

    async def handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                    continue

                msg_type = data.get("type")
                if msg_type == "register_task":
                    task = data.get("task")
                    if task:
                        self.tasks.append(task)
                        await self.broadcast_tasks()
                elif msg_type == "request_tasks":
                    await websocket.send(json.dumps({"type": "tasks", "tasks": self.tasks}))
                elif msg_type == "propose_patch":
                    await self.handle_patch(data, websocket)
                else:
                    await websocket.send(json.dumps({"type": "error", "message": "Unknown message type"}))
        finally:
            await self.unregister(websocket)

    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        async with websockets.serve(self.handler, host, port):
            logging.info("Universal IDE bridge listening on ws://%s:%d", host, port)
            await asyncio.Future()  # run forever


if __name__ == "__main__":
    bridge = IDEBridge()
    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        logging.info("IDE bridge stopped")
