from typing import Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Message(BaseModel):
    message: str


@router.post("/echo", name="send_echo_message")
async def echo(message: Message) -> Dict[str, str]:
    return {"message": message.message}
