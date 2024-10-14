from fastapi import APIRouter, Depends, WebSocket
from backend.commons.responses import ServiceResponse
from backend.db.dependencies import get_db_session
from backend.db.models.users import User , current_active_user
from backend.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
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
    path: str,
    db: AsyncSession = Depends(get_db_session),
) -> ServiceResponse:
    manager =  LiveFeed()
    result = await manager.process_video(path ,db)
    return result
