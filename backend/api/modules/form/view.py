from fastapi import APIRouter, Depends, WebSocket
from backend.commons.responses import ServiceResponse
from backend.db.dependencies import get_db_session
from backend.db.models.users import User , current_active_user
from backend.logging import get_logger
from backend.services.base.cam import LiveFeed
router = APIRouter()

logger = get_logger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    manager = LiveFeed()
    await manager.connect(websocket)
    result = await manager.send_personal_message("Connected", websocket)
    return result

@router.put("/fill", response_model=None)
async def list_processes(
    path: str
) -> ServiceResponse:
    manager =  LiveFeed()
    result = manager.process_video(path)
    return result
