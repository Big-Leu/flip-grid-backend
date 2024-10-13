import uuid
from fastapi import WebSocket
from backend.logging import get_logger
from backend.services.commons.base import BaseService
logger = get_logger(__name__)


class LiveFeed(BaseService):
    __item_name__ = "FormService"

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        id = uuid.uuid4()
        video_path = f"backend/services/video/{id}.mkv"
        try:
            with open(video_path, "wb") as video_file:
                while True:
                    try:
                        print("Receiving data")
                        data = await websocket.receive_bytes()
                        if not data:
                            print("data null")
                            break 
                        print("recived data")
                        video_file.write(data)
                        print("data written")
                    except Exception as e:
                        print(f"Error receiving data: {e}")
                        break
        except Exception as e:
            print(f"File handling error: {e}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)